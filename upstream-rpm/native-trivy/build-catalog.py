#!/usr/bin/env python3
"""Build a public artifact catalogue from the published RPM bundle on EL8.

This pins artifacts, not a complete advisory feed. One reviewed bzip2 CVE is
included as a proof of integration. Requires Python 3.6+ and rpm CLI.
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
    args = parser.parse_args()
    manifest = args.bundle / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    files = {row["path"]: row["sha256"] for row in data["files"]}
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
        # Curated assessment is tied to this exact already reviewed artifact.
        if expected == "7cfbe70625b0d6e6b9a1a0dd0a8a934769ee8941a1cf3c50a836981134aed9cd":
            raw = subprocess.check_output(["rpm", "-qp", "--qf", "[%{FILENAMES}\t%{FILEDIGESTS}\n]", str(path)], universal_newlines=True)
            digests = dict(line.split("\t") for line in raw.splitlines())
            recover = "/usr/bin/bzip2recover"
            if digests[recover] != "9a02c954f550943da56f526a470017a292fc4e95f3ea787ab146ae7901771283":
                raise ValueError("Reviewed executable digest changed")
            row["files"] = {recover: digests[recover]}
            row["assessments"] = [{
                "cve": "CVE-2026-42250", "status": "fixed",
                "scope": "bzip2recover only; no assertion about other bzip2 CVEs or libbz2",
                "advisory": "https://cert.pl/en/posts/2026/05/CVE-2026-42250/",
                "patch_commit": "35d122a3df8b0cc4082a4d89fdc6ee99f375fe67",
                "evidence": "https://github.com/emotionbug/slop/blob/5c97ae13b38655ecf5b76dda0bca5dd7c888afba/upstream-rpm/SECURITY-EVIDENCE.md",
                "verification": "Previously recorded ASan original/patched regression and installed bzip2recover output protection tests"}]
        artifacts.append(row)
    if not artifacts:
        raise ValueError("No custom RPMs found")
    catalog = {"schema_version": 1, "scope": "Artifact linkage PoC; one reviewed CVE, incomplete advisory coverage",
               "bundle_manifest_sha256": sha(manifest), "artifacts": artifacts}
    args.output.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Catalogue artifacts: {}".format(len(artifacts)))


if __name__ == "__main__":
    main()
