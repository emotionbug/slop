#!/usr/bin/env python3
"""Read-only ELF import audit. No packages, services or files are changed.

This finds direct undefined dynamic symbols and COPY relocations, not dlsym string lookups, future
plugins, containers, unmounted filesystems or currently loaded deleted files.
An empty result is not proof that a library replacement is safe.
"""
import argparse
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys

SYMBOLS = {'ZSTD_getSequences', 'jpeg_std_message_table'}
DEFAULT_ROOTS = ['/usr/bin', '/usr/sbin', '/usr/lib', '/usr/lib64', '/usr/libexec', '/opt', '/usr/local']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('roots', nargs='*', help='Application paths to scan IN ADDITION to the defaults')
    parser.add_argument('--only-roots', action='store_true',
                        help='Scan only the supplied paths (for targeted checks; omits default coverage)')
    args = parser.parse_args()
    if args.only_roots and not args.roots:
        parser.error('--only-roots requires at least one path')
    if not shutil.which('readelf'):
        raise SystemExit('readelf is required (binutils package)')
    roots = list(dict.fromkeys(([] if args.only_roots else DEFAULT_ROOTS) + args.roots))
    seen, matches, errors = set(), [], []
    directory_links = {}
    directory_roots = [os.path.realpath(p) for p in roots if os.path.isdir(p)]
    scanned = 0

    def record_error(path, error):
        item = {'path':str(path), 'error':str(error)[:300]}
        if isinstance(error, FileNotFoundError):
            item['kind'] = 'missing_path'
            try:
                if pathlib.Path(path).is_symlink():
                    item.update(kind='broken_symlink', link_target=os.readlink(str(path)),
                                resolved_target=os.path.realpath(str(path)))
            except OSError:
                pass
        elif isinstance(error, PermissionError):
            item['kind'] = 'permission_denied'
        else:
            item['kind'] = 'inspection_failed'
        errors.append(item)

    def walk_error(error):
        record_error(error.filename, error)

    def walk_files(root):
        for base, directories, names in os.walk(os.path.realpath(str(root)),
                                                followlinks=False, onerror=walk_error):
            for name in directories:
                path = os.path.join(base, name)
                if os.path.islink(path):
                    target = os.path.realpath(path)
                    # Directory links are not followed; tell the operator about
                    # targets not already reachable through a declared root.
                    covered = any(os.path.commonpath([target, entry]) == entry
                                  for entry in directory_roots)
                    if not covered:
                        directory_links[path] = {'path':path, 'resolved_target':target}
            for name in names:
                yield os.path.join(base, name)

    for entry in roots:
        root = pathlib.Path(entry)
        try:
            root_stat = root.stat()
        except OSError as error:
            record_error(root, error)
            continue
        if stat.S_ISREG(root_stat.st_mode):
            files = [str(root)]
        elif stat.S_ISDIR(root_stat.st_mode):
            files = walk_files(root)
        else:
            record_error(root, ValueError('Root is not a regular file or directory'))
            continue
        for filename in files:
            try:
                p = pathlib.Path(filename)
                file_stat = p.stat()
                if not stat.S_ISREG(file_stat.st_mode) or (file_stat.st_dev,file_stat.st_ino) in seen:
                    continue
                seen.add((file_stat.st_dev,file_stat.st_ino))
                with p.open('rb') as stream:
                    if stream.read(4) != b'\x7fELF':
                        continue
                result = subprocess.run(['readelf','--dyn-syms','--wide',str(p)],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,
                    errors='replace',timeout=30,env=dict(os.environ,LC_ALL='C'))
                if result.returncode:
                    record_error(p, ValueError(result.stderr.strip() or 'readelf failed'))
                    continue
                scanned += 1
                found = set()
                defined_targets = set()
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if len(parts)>=8 and parts[0].rstrip(':').isdigit():
                        name = parts[7].split('@')[0]
                        if name in SYMBOLS:
                            (found if parts[6]=='UND' else defined_targets).add(name)
                if defined_targets:
                    # Executables using exported data can have a defined symbol
                    # plus a loader COPY relocation, rather than an UND entry.
                    rel = subprocess.run(['readelf','--relocs','--wide',str(p)],
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,
                        errors='replace',timeout=30,env=dict(os.environ,LC_ALL='C'))
                    if rel.returncode:
                        record_error(p, ValueError(rel.stderr.strip() or 'readelf relocations failed'))
                    else:
                        for line in rel.stdout.splitlines():
                            parts = line.split()
                            if len(parts)>=5 and parts[2].endswith('_COPY'):
                                name = parts[4].split('@')[0]
                                if name in SYMBOLS:
                                    found.add(name)
                if found:
                    matches.append({'path':str(p),'symbols':sorted(found)})
            except (OSError, subprocess.TimeoutExpired) as error:
                record_error(filename, error)
    print(json.dumps({'audit_version':2,'read_only':True,'roots':roots,'elf_files_scanned':scanned,
        'symbols_checked':sorted(SYMBOLS),'direct_import_matches':matches,'errors':errors,
        'directory_symlinks_outside_roots':sorted(directory_links.values(), key=lambda item:item['path']),
        'coverage_complete_for_declared_roots':not errors and not directory_links,
        'limit':'ELF imports and COPY relocations only. Does not clear dlsym/plugins/containers/unmounted paths or target compatibility.'},
        ensure_ascii=False,indent=2))
    return 2 if errors or directory_links else (1 if matches else 0)


if __name__ == '__main__':
    sys.exit(main())
