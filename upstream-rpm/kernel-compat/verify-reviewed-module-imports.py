#!/usr/bin/env python3
"""Compare reviewed external module CRC imports with one kernel build.

The input analysis is produced from private module binaries, but this report
contains only symbol names and CRC comparison results.  It does not copy,
modify, load, or redistribute a vendor module.
"""
import argparse
import json
from pathlib import Path


def load_symvers(path):
    symbols = {}
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        fields = line.split()
        if len(fields) < 3:
            raise ValueError('Malformed Module.symvers line {}: {}'.format(number, line))
        crc, name = fields[:2]
        symbols[name] = int(crc, 16)
    return symbols


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--symvers', type=Path, required=True)
    parser.add_argument('--module-sha256', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    analysis = json.loads(args.analysis.read_text(encoding='utf-8'))
    selected = {}
    requested = set(args.module_sha256)
    for filename, item in analysis['files'].items():
        if item['sha256'] in requested:
            selected[item['sha256']] = (filename, item)
    missing_profiles = sorted(requested - set(selected))
    if missing_profiles:
        raise ValueError('Missing reviewed profile(s): ' + ', '.join(missing_profiles))

    providers = load_symvers(args.symvers)
    provider_kind = {name: 'kernel' for name in providers}
    for filename, item in selected.values():
        for name, crc in item.get('exports', {}).items():
            existing = providers.get(name)
            if existing is not None and existing != crc:
                raise ValueError('Conflicting provider CRC for {}'.format(name))
            providers[name] = crc
            provider_kind[name] = filename

    modules = []
    totals = {'imports': 0, 'matched': 0, 'crc_mismatch': 0, 'missing': 0}
    for sha256 in args.module_sha256:
        filename, item = selected[sha256]
        mismatches = []
        missing = []
        matched = 0
        provider_counts = {}
        for name, expected in sorted(item.get('imports', {}).items()):
            actual = providers.get(name)
            if actual is None:
                missing.append(name)
                continue
            if actual != expected:
                mismatches.append({
                    'symbol': name,
                    'expected_crc': '0x{:08x}'.format(expected),
                    'actual_crc': '0x{:08x}'.format(actual),
                    'provider': provider_kind[name],
                })
                continue
            matched += 1
            provider = provider_kind[name]
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        count = len(item.get('imports', {}))
        modules.append({
            'file': filename,
            'sha256': sha256,
            'imports': count,
            'matched': matched,
            'crc_mismatch': mismatches,
            'missing': missing,
            'matched_providers': dict(sorted(provider_counts.items())),
            'compatible': matched == count,
        })
        totals['imports'] += count
        totals['matched'] += matched
        totals['crc_mismatch'] += len(mismatches)
        totals['missing'] += len(missing)

    report = {
        'schema_version': 1,
        'scope': ('Static CONFIG_MODVERSIONS import check against the exact '
                  'kernel Module.symvers and reviewed peer-module exports.'),
        'symvers': str(args.symvers),
        'modules': modules,
        'totals': totals,
        'compatible': totals['matched'] == totals['imports'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(totals, sort_keys=True))
    if not report['compatible']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
