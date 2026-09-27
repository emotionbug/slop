#!/usr/bin/env python3
"""Apply official CNA fix patches that need bounded context fuzz.

This is deliberately separate from the clean-apply planner.  It verifies every
cached patch hash, accepts an exact apply first, then permits GNU patch fuzz up
to the requested bound without rejects.  Multiple passes allow prerequisite
fixes applied earlier in the plan to make later patches applicable.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def run(command, source):
    result = subprocess.run(command, cwd=str(source), universal_newlines=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.returncode, result.stdout.strip()


def git_check(source, patch, reverse=False):
    if not shutil.which('git'):
        command = ['patch', '--dry-run', '-p1', '--batch', '--fuzz=0',
                   '--input', str(patch)]
        command.insert(4, '--reverse' if reverse else '--forward')
        return run(command, source)
    command = ['git', 'apply', '--check', '--recount']
    if reverse:
        command.append('--reverse')
    command.append(str(patch))
    return run(command, source)


def patch_check(source, patch, fuzz, dry_run):
    command = ['patch', '-p1', '--batch', '--forward',
               '--fuzz={}'.format(fuzz), '--input', str(patch)]
    if dry_run:
        command.insert(1, '--dry-run')
    return run(command, source)


def try_item(item, source, cache, fuzz):
    diagnostics = []
    for check in item['patch_checks']:
        patch = cache / (check['commit'] + '.patch')
        data = patch.read_bytes()
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != check['patch_sha256']:
            raise ValueError('{}: patch hash mismatch'.format(check['commit']))
        reverse_rc, reverse_out = git_check(source, patch, reverse=True)
        if reverse_rc == 0:
            return {'status': 'already-present', 'commit': check['commit'],
                    'patch_sha256': actual_hash, 'diagnostic': reverse_out}
        forward_rc, forward_out = git_check(source, patch)
        if forward_rc == 0:
            if shutil.which('git'):
                command = ['git', 'apply', '--recount', str(patch)]
            else:
                command = ['patch', '-p1', '--batch', '--forward', '--fuzz=0',
                           '--input', str(patch)]
            apply_rc, apply_out = run(command, source)
            if apply_rc:
                raise RuntimeError('{}: exact apply changed after check: {}'.format(
                    check['commit'], apply_out))
            return {'status': 'applied-exact', 'commit': check['commit'],
                    'patch_sha256': actual_hash, 'diagnostic': apply_out}
        dry_rc, dry_out = patch_check(source, patch, fuzz, dry_run=True)
        diagnostics.append({'commit': check['commit'],
                            'exact': forward_out[:1000],
                            'fuzzy': dry_out[:2000]})
        if dry_rc == 0:
            apply_rc, apply_out = patch_check(
                source, patch, fuzz, dry_run=False)
            if apply_rc:
                raise RuntimeError('{}: fuzzy apply changed after check: {}'.format(
                    check['commit'], apply_out))
            return {'status': 'applied-fuzzy', 'commit': check['commit'],
                    'patch_sha256': actual_hash,
                    'diagnostic': apply_out[:4000]}
    return {'status': 'not-applicable', 'diagnostics': diagnostics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checks', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fuzz', type=int, default=2)
    parser.add_argument('--passes', type=int, default=3)
    args = parser.parse_args()
    if args.fuzz < 0 or args.fuzz > 3:
        parser.error('--fuzz must be between 0 and 3')
    checks = json.loads(args.checks.read_text(encoding='utf-8'))
    selected = [item for item in checks['items'] if item['status'] in {
        'inconclusive-context-drift', 'fix-absent-forward-apply'}]
    pending = {item['cve']: item for item in selected}
    results = {}
    pass_counts = []
    for pass_number in range(1, args.passes + 1):
        changed = 0
        for cve in sorted(list(pending)):
            result = try_item(pending[cve], args.source, args.cache, args.fuzz)
            result['pass'] = pass_number
            if result['status'] != 'not-applicable':
                results[cve] = result
                del pending[cve]
                changed += 1
                print(cve, result['status'], result.get('commit', ''), flush=True)
        pass_counts.append({'pass': pass_number, 'applied_or_present': changed,
                            'remaining': len(pending)})
        if changed == 0:
            break
    for cve, item in pending.items():
        result = try_item(item, args.source, args.cache, args.fuzz)
        result['pass'] = len(pass_counts)
        results[cve] = result
    counts = {}
    for result in results.values():
        status = result['status']
        counts[status] = counts.get(status, 0) + 1
    output = {
        'schema_version': 1,
        'scope': ('Official Linux stable patches only; exact cached hashes; '
                  'GNU patch with bounded fuzz and no rejects.'),
        'fuzz': args.fuzz,
        'passes': pass_counts,
        'counts': counts,
        'items': [{'cve': cve, **results[cve]} for cve in sorted(results)],
    }
    with args.output.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(output, indent=2) + '\n')
    print(json.dumps(counts, sort_keys=True))


if __name__ == '__main__':
    main()
