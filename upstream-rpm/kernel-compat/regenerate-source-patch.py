#!/usr/bin/env python3
"""Create an applyable source-only patch from two kernel trees.

Kernel builds leave gigabytes of objects and generated headers in the working
tree.  This tool compares every file that existed in the clean baseline, plus
explicitly source-like files newly added by backports, while excluding build
products.  It is intentionally independent of Git metadata in the SRPM tree.
"""
from __future__ import print_function

import argparse
import difflib
import os
from pathlib import Path


SOURCE_SUFFIXES = {
    ".c", ".h", ".s", ".S", ".lds", ".dts", ".dtsi", ".yaml", ".yml",
    ".json", ".rst", ".txt", ".pl", ".py", ".sh",
}
SOURCE_NAMES = {"Kbuild", "Kconfig", "Makefile"}
SKIP_PARTS = {
    ".git", ".tmp_versions", "include/generated", "include/config",
    "usr/include",
}


def relative_files(root):
    result = set()
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel == item or rel.startswith(item + "/") for item in SKIP_PARTS):
            continue
        result.add(rel)
    return result


def source_like(rel):
    path = Path(rel)
    return path.suffix in SOURCE_SUFFIXES or path.name in SOURCE_NAMES or \
        path.name.startswith("Kconfig.") or path.name.startswith("Makefile.")


def read_text(path):
    data = path.read_bytes()
    if b"\0" in data:
        raise UnicodeError("binary file")
    return data.decode("utf-8", "surrogateescape").splitlines(True)


def patch_added_files(cache):
    allowed = set()
    if cache is None:
        return allowed
    for patch in cache.glob("*.patch"):
        previous = ""
        for line in patch.read_text(
                encoding="utf-8", errors="surrogateescape").splitlines():
            if previous == "--- /dev/null" and line.startswith("+++ b/"):
                allowed.add(line[6:].split("\t", 1)[0])
            previous = line
    return allowed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--patch-cache", type=Path,
                        help="include source files added by patches in this directory")
    args = parser.parse_args()

    baseline_files = relative_files(args.baseline)
    current_files = relative_files(args.current)
    allowed_added = patch_added_files(args.patch_cache)
    candidates = sorted(baseline_files | {
        rel for rel in current_files - baseline_files
        if source_like(rel) and rel in allowed_added
    })

    changed = []
    added = []
    removed = []
    skipped_binary = []
    output = []
    for rel in candidates:
        before_path = args.baseline / rel
        after_path = args.current / rel
        try:
            before = read_text(before_path) if before_path.exists() else []
            after = read_text(after_path) if after_path.exists() else []
        except UnicodeError:
            if before_path.exists() and after_path.exists() and \
                    before_path.read_bytes() != after_path.read_bytes():
                skipped_binary.append(rel)
            continue
        if before == after:
            continue
        changed.append(rel)
        if not before_path.exists():
            added.append(rel)
        if not after_path.exists():
            removed.append(rel)
        output.extend(difflib.unified_diff(
            before,
            after,
            fromfile="a/" + rel,
            tofile="b/" + rel,
            lineterm="\n",
        ))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", errors="surrogateescape") as handle:
        handle.write("".join(output))
    print("changed={0} added={1} removed={2} skipped_binary={3} bytes={4}".format(
        len(changed), len(added), len(removed), len(skipped_binary),
        args.output.stat().st_size))
    if added:
        print("added_source_files=" + ",".join(added))
    if removed:
        print("removed_source_files=" + ",".join(removed))
    if skipped_binary:
        print("skipped_binary_files=" + ",".join(skipped_binary))


if __name__ == "__main__":
    main()
