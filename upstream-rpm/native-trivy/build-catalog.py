#!/usr/bin/env python3
"""Build a public artifact catalogue from the published RPM bundle on EL8.

Pins RPMs, source RPMs, immutable payloads and explicitly reviewed CVEs.
Requires Python 3.6+ and rpm CLI. Reviews apply only to their exact RPM SHA-256.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

TAGS = ("NAME", "EPOCHNUM", "VERSION", "RELEASE", "ARCH", "VENDOR", "SOURCERPM", "SHA256HEADER")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, default=Path(__file__).with_name("reviewed-evidence.json"))
    parser.add_argument("--source-projects", type=Path, default=Path(__file__).with_name("source-projects.json"))
    args = parser.parse_args()
    manifest = args.bundle / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    files = {row["path"]: row["sha256"] for row in data["files"]}
    reviews = json.loads(args.reviews.read_text(encoding="utf-8"))["artifacts"]
    source_projects = json.loads(args.source_projects.read_text(encoding="utf-8"))["artifacts"]
    artifacts = []
    for rel, expected in sorted(files.items()):
        if not rel.startswith("rpms/") or not rel.endswith(".rpm"):
            continue
        path = (args.bundle / rel).resolve()
        if args.bundle.resolve() not in path.parents or sha(path) != expected:
            raise ValueError("Bundle path/digest mismatch: " + rel)
        fmt = "\t".join("%{" + tag + "}" for tag in TAGS)
        values = subprocess.check_output(["rpm", "-qp", "--qf", fmt, str(path)], universal_newlines=True).split("\t")
        row = dict(zip((t.lower() for t in TAGS), values))
        srpm = "srpms/" + row["sourcerpm"]
        # RPM's SOURCERPM tag can retain .src.rpm when a large test-only
        # NoSource archive makes the emitted source package .nosrc.rpm.
        if srpm not in files and srpm.endswith('.src.rpm'):
            alternate = srpm[:-8] + '.nosrc.rpm'
            if alternate in files:
                srpm = alternate
        source_hash = files.get(srpm, "")
        override = source_projects.get(source_hash, {})
        if row["vendor"] != "Linux OSS local build" and not override.get("include_nonstandard_vendor", False):
            continue
        if srpm not in files or sha(args.bundle / srpm) != files[srpm]:
            raise ValueError("Source RPM missing or digest mismatch: " + srpm)
        row.update(rpm_sha256=expected, srpm_sha256=files[srpm], files={}, assessments=[])
        row['source_archive'] = Path(srpm).name
        row["project"] = row["sourcerpm"].rsplit("-", 2)[0]
        row["project"] = override.get("project", row["project"])
        row["components"] = override.get("components", [])
        role = override.get("package_roles", {}).get(row["name"])
        if role:
            if role not in ("configuration-only", "filesystem-only"):
                raise ValueError("Unsupported component role")
            row["component_role"] = role
        raw = subprocess.check_output(["rpm", "-qp", "--qf", "[%{FILENAMES}\t%{FILEDIGESTS}\t%{FILEFLAGS}\n]", str(path)], universal_newlines=True)
        for line in raw.splitlines():
            filename, digest, flags = line.split("\t")
            if len(digest) == 64 and not (int(flags) & 1):
                row["files"][filename] = digest
        row["assessments"] = reviews.get(expected, [])
        if row.get("component_role") in ("configuration-only", "filesystem-only") and row["files"]:
            raise ValueError("Configuration-only review disagrees with payload")
        artifacts.append(row)
    if not artifacts:
        raise ValueError("No custom RPMs found")
    catalog = {"schema_version": 1, "scope": "Exact custom artifacts and reviewed evidence; selected upstream feed coverage remains incomplete",
               "reviewed_evidence_sha256": sha(args.reviews), "source_projects_sha256": sha(args.source_projects),
               "bundle_manifest_sha256": sha(manifest), "artifacts": artifacts}
    args.output.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Catalogue artifacts: {}".format(len(artifacts)))


if __name__ == "__main__":
    main()
