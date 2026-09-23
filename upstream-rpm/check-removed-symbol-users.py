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
import subprocess
import sys

SYMBOLS = {'ZSTD_getSequences', 'jpeg_std_message_table'}
DEFAULT_ROOTS = ['/usr/bin', '/usr/sbin', '/usr/lib64', '/usr/libexec', '/opt', '/usr/local']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('roots', nargs='*', help='Additional/explicit application directories to scan')
    args = parser.parse_args()
    if not shutil.which('readelf'):
        raise SystemExit('readelf is required (binutils package)')
    roots = args.roots or DEFAULT_ROOTS
    seen, matches, errors = set(), [], []
    scanned = 0

    def walk_error(error):
        errors.append({'path':error.filename, 'error':str(error)})

    for entry in roots:
        root = pathlib.Path(entry)
        if not root.exists():
            errors.append({'path':str(root), 'error':'Path is absent'})
            continue
        if root.is_file():
            files = [str(root)]
        else:
            files = (os.path.join(base,name) for base,_,names in
                     os.walk(str(root.resolve()), followlinks=False, onerror=walk_error) for name in names)
        for filename in files:
            try:
                p = pathlib.Path(filename)
                stat = p.stat()
                if not p.is_file() or (stat.st_dev,stat.st_ino) in seen:
                    continue
                seen.add((stat.st_dev,stat.st_ino))
                with p.open('rb') as stream:
                    if stream.read(4) != b'\x7fELF':
                        continue
                result = subprocess.run(['readelf','--dyn-syms','--wide',str(p)],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,
                    errors='replace',timeout=30,env=dict(os.environ,LC_ALL='C'))
                if result.returncode:
                    errors.append({'path':str(p),'error':result.stderr.strip()[:300]})
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
                        errors.append({'path':str(p),'error':rel.stderr.strip()[:300]})
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
                errors.append({'path':filename,'error':str(error)[:300]})
    print(json.dumps({'read_only':True,'roots':roots,'elf_files_scanned':scanned,
        'symbols_checked':sorted(SYMBOLS),'direct_import_matches':matches,'errors':errors,
        'limit':'ELF imports and COPY relocations only. Does not clear dlsym/plugins/containers/unmounted paths or target compatibility.'},
        ensure_ascii=False,indent=2))
    return 2 if errors else (1 if matches else 0)


if __name__ == '__main__':
    sys.exit(main())
