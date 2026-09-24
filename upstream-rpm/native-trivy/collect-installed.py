#!/usr/bin/env python3
"""Read local RPM identities and security-relevant executable hashes. No changes."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

TAGS = ("NAME", "EPOCHNUM", "VERSION", "RELEASE", "ARCH", "VENDOR", "SOURCERPM", "SHA256HEADER")


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.catalog.read_bytes()
    catalog = json.loads(raw.decode("utf-8"))
    trusted_paths = {path for row in catalog["artifacts"] for path in row["files"]}
    checked = {}
    for path in sorted(trusted_paths):
        try:
            checked[path] = {"sha256": sha_file(path)}
        except OSError as exc:
            checked[path] = {"error": str(exc)}
    fmt = "\t".join("%{" + tag + "}" for tag in TAGS) + "\n"
    raw_rpms = subprocess.check_output(["rpm", "-qa", "--qf", fmt], universal_newlines=True)
    packages = []
    for line in raw_rpms.splitlines():
        values = line.split("\t")
        if len(values) != len(TAGS):
            raise ValueError("Unexpected RPM query row")
        row = dict(zip((t.lower() for t in TAGS), values))
        if row["vendor"] == "Linux OSS local build" or "linuxoss" in row["release"]:
            packages.append(row)
    snapshot = {"schema_version": 1, "catalog_sha256": hashlib.sha256(raw).hexdigest(),
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "packages": sorted(packages, key=lambda p: (p["name"], p["arch"], p["version"])),
                "checked_files": checked}
    # Refuse to overwrite old or symlinked evidence files.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(snapshot, stream, indent=2)
        stream.write("\n")
    print("Captured {} custom RPMs".format(len(packages)))


if __name__ == "__main__":
    main()
