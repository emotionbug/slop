#!/usr/bin/env python3
"""Read-only module import comparison. Matching CRCs are not runtime proof."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module_symbols(path, option):
    output = subprocess.check_output(['modprobe', option, str(path)], text=True)
    result = {}
    for line in output.splitlines():
        crc, name = line.split()
        if name in result:
            raise ValueError('Duplicate module symbol: ' + name)
        result[name] = int(crc, 16)
    return result


def compare(imports, providers):
    matched, different, missing = [], {}, []
    for name, expected in sorted(imports.items()):
        if name not in providers:
            missing.append(name)
        elif providers[name]['crc'] != expected:
            different[name] = {'expected': hex(expected),
                               'actual': hex(providers[name]['crc']),
                               'provider': providers[name]['source']}
        else:
            matched.append(name)
    return {'import_count': len(imports), 'matches': matched,
            'mismatches': different, 'missing': missing}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symvers', type=Path, nargs='+', required=True)
    parser.add_argument('--peer', type=Path, action='append', default=[])
    parser.add_argument('--module', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    providers = {}

    def add(name, crc, source):
        if name in providers:
            raise ValueError('Ambiguous duplicate symbol provider: ' + name)
        providers[name] = {'crc': crc, 'source': source}

    for path in args.symvers:
        for line in path.read_text().splitlines():
            crc, name, provider, *_ = line.split()
            add(name, int(crc, 16), provider)
    for path in args.peer:
        for name, crc in module_symbols(path, '--show-exports').items():
            add(name, crc, path.name)
    modules = []
    for path in args.module:
        item = {'file': path.name, 'sha256': digest(path),
                'vermagic': subprocess.check_output(
                    ['modinfo', '-F', 'vermagic', str(path)], text=True).strip()}
        item.update(compare(module_symbols(path, '--show-modversions'), providers))
        modules.append(item)
    result = {'schema_version': 1, 'scope': 'static-versioned-import-comparison-only',
              'runtime_compatible': False,
              'inputs': [{'file': p.name, 'sha256': digest(p)} for p in args.symvers + args.peer],
              'modules': modules}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    for item in modules:
        print(json.dumps({'file': item['file'], 'imports': item['import_count'],
                          'matched': len(item['matches']),
                          'mismatched': len(item['mismatches']), 'missing': item['missing']}))


if __name__ == '__main__':
    main()
