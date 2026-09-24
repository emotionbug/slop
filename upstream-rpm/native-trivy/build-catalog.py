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
    args = parser.parse_args()
    manifest = args.bundle / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    files = {row["path"]: row["sha256"] for row in data["files"]}
    reviews = json.loads(args.reviews.read_text(encoding="utf-8"))["artifacts"]
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
        if row["vendor"] != "Linux OSS local build":
            continue
        srpm = "srpms/" + row["sourcerpm"]
        if srpm not in files or sha(args.bundle / srpm) != files[srpm]:
            raise ValueError("Source RPM missing or digest mismatch: " + srpm)
        row.update(rpm_sha256=expected, srpm_sha256=files[srpm], files={}, assessments=[])
        row["project"] = row["sourcerpm"].rsplit("-", 2)[0]
        row["components"] = ([{"project": "xxhash", "version": "0.8.4"}] if row["name"] == "rsync" else [])
        raw = subprocess.check_output(["rpm", "-qp", "--qf", "[%{FILENAMES}\t%{FILEDIGESTS}\t%{FILEFLAGS}\n]", str(path)], universal_newlines=True)
        for line in raw.splitlines():
            filename, digest, flags = line.split("\t")
            if len(digest) == 64 and not (int(flags) & 1):
                row["files"][filename] = digest
        row["assessments"] = reviews.get(expected, [])
        artifacts.append(row)
    if not artifacts:
        raise ValueError("No custom RPMs found")
    catalog = {"schema_version": 1, "scope": "Exact custom artifacts and reviewed evidence; selected upstream feed coverage remains incomplete",
               "reviewed_evidence_sha256": sha(args.reviews),
               "bundle_manifest_sha256": sha(manifest), "artifacts": artifacts}
    args.output.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Catalogue artifacts: {}".format(len(artifacts)))


if __name__ == "__main__":
    main()
