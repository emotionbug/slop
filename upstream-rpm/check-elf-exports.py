#!/usr/bin/env python3
"""Check exported symbol presence; this is not a complete C/C++ ABI checker."""
import argparse
import json
import pathlib
import subprocess


def exports(path):
    result = subprocess.run(['readelf', '--dyn-syms', '--wide', path],
                            check=True, stdout=subprocess.PIPE, universal_newlines=True)
    names = set()
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].rstrip(':').isdigit():
            continue
        if fields[4] not in ('GLOBAL', 'WEAK') or fields[6] == 'UND':
            continue
        if fields[5] not in ('DEFAULT', 'PROTECTED'):
            continue
        symbol = fields[7]
        if '@@' in symbol:
            # Default versions satisfy both unversioned and versioned callers.
            names.add(symbol.split('@@')[0])
            names.add(symbol.replace('@@', '@'))
        else:
            names.add(symbol)
    if not names:
        raise RuntimeError('No dynamic exports found: ' + path)
    return sorted(names)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=('snapshot', 'compare'))
    ap.add_argument('snapshot', type=pathlib.Path)
    ap.add_argument('libraries', nargs='*')
    args = ap.parse_args()
    if args.action == 'snapshot':
        if not args.libraries:
            ap.error('snapshot requires library paths')
        data = {path: exports(path) for path in args.libraries}
        args.snapshot.write_text(json.dumps(data, indent=2) + '\n')
        print('ELF_EXPORT_SNAPSHOT', len(data))
        return
    baseline = json.loads(args.snapshot.read_text())
    missing = {}
    for path, symbols in baseline.items():
        absent = sorted(set(symbols) - set(exports(path)))
        print('ELF_EXPORT_COMPARE', path, 'baseline=' + str(len(symbols)),
              'missing=' + str(len(absent)))
        if absent:
            missing[path] = absent
    if missing:
        print(json.dumps(missing, indent=2))
        raise SystemExit(1)
    print('ELF_EXPORT_PRESENCE_OK; data layouts, semantics and dlopen users not checked')


if __name__ == '__main__':
    main()
