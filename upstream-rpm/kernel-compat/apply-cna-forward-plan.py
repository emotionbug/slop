#!/usr/bin/env python3
"""Apply clean CNA fixes to an EL8 kernel tree and emit one reviewable patch."""
import argparse
from email.utils import mktime_tz, parsedate_tz
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess


DATE = re.compile(br'(?m)^Date: (.+)$')
PATCH_PATH = re.compile(br'(?m)^(?:--- a|\+\+\+ b)/([^\t\n]+)')


def run_patch(source, patch, reverse=False, dry_run=True):
    # This planner is the exact-apply lane.  GNU patch otherwise enables
    # context fuzz implicitly and would make the report overstate its gate.
    command = ['patch', '-p1', '--batch', '--fuzz=0', '--forward']
    if dry_run:
        command.append('--dry-run')
    if reverse:
        command.append('--reverse')
    command.extend(['--input', str(patch)])
    result = subprocess.run(command, cwd=str(source), universal_newlines=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.returncode == 0, result.stdout.strip()[:2000]


def patch_timestamp(data):
    match = DATE.search(data)
    if not match:
        return 0
    parsed = parsedate_tz(match.group(1).decode(errors='replace'))
    return int(mktime_tz(parsed)) if parsed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checks', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--patch-output', type=Path, required=True)
    parser.add_argument('--report-output', type=Path, required=True)
    parser.add_argument('--extra-path', action='append', default=[])
    parser.add_argument('--include-report', type=Path, action='append', default=[])
    args = parser.parse_args()
    if args.source.resolve() == args.baseline.resolve():
        parser.error('--source and --baseline must differ')

    check_bytes = args.checks.read_bytes()
    checks = json.loads(check_bytes)
    selected = []
    for item in checks['items']:
        if item['status'] != 'fix-absent-forward-apply':
            continue
        match = next(check for check in item['patch_checks']
                     if check['forward']['applies'])
        patch = args.cache / (match['commit'] + '.patch')
        data = patch.read_bytes()
        if hashlib.sha256(data).hexdigest() != match['patch_sha256']:
            raise ValueError(item['cve'] + ': cached patch hash changed')
        selected.append((patch_timestamp(data), item['cve'], match, patch, data))
    selected.sort(key=lambda row: (row[0], row[1], row[2]['commit']))

    touched = set(args.extra_path)
    for report_path in args.include_report:
        previous = json.loads(report_path.read_text(encoding='utf-8'))
        for outcome in previous['outcomes']:
            touched.update(outcome.get('paths', []))
    outcomes = []
    seen = {}
    for timestamp, cve, check, patch, data in selected:
        identity = check['patch_sha256']
        if identity in seen:
            outcomes.append({'cve': cve, 'status': 'duplicate-patch',
                             'same_as': seen[identity], 'commit': check['commit']})
            continue
        seen[identity] = cve
        paths = sorted({match.decode() for match in PATCH_PATH.findall(data)
                        if match != b'/dev/null'})
        reverse, reverse_log = run_patch(args.source, patch, reverse=True)
        if reverse:
            status = 'already-present-in-working-tree'
            diagnostic = reverse_log
        else:
            forward, forward_log = run_patch(args.source, patch)
            if not forward:
                outcomes.append({'cve': cve, 'status': 'conflict-after-prior-fixes',
                                 'commit': check['commit'],
                                 'diagnostic': forward_log})
                continue
            applied, apply_log = run_patch(args.source, patch, dry_run=False)
            if not applied:
                raise RuntimeError(cve + ': dry-run passed but application failed: ' + apply_log)
            status = 'applied'
            diagnostic = apply_log
        touched.update(paths)
        outcomes.append({'cve': cve, 'status': status, 'commit': check['commit'],
                         'patch_sha256': identity, 'paths': paths,
                         'diagnostic': diagnostic})

    with args.patch_output.open('w', encoding='utf-8', newline='\n') as stream:
        for relative in sorted(touched):
            before_path = args.baseline / relative
            after_path = args.source / relative
            before = (before_path.read_text(encoding='utf-8').splitlines(True)
                      if before_path.exists() else [])
            after = (after_path.read_text(encoding='utf-8').splitlines(True)
                     if after_path.exists() else [])
            stream.writelines(difflib.unified_diff(
                before, after, fromfile='a/' + relative, tofile='b/' + relative))

    counts = {}
    for outcome in outcomes:
        status = outcome['status']
        counts[status] = counts.get(status, 0) + 1
    report = {
        'schema_version': 1,
        'scope': ('Applies only patches that passed a forward dry-run against the '
                  'pinned baseline; compile, kABI and runtime gates remain required.'),
        'checks_sha256': hashlib.sha256(check_bytes).hexdigest(),
        'combined_patch_sha256': hashlib.sha256(
            args.patch_output.read_bytes()).hexdigest(),
        'counts': counts,
        'outcomes': outcomes,
    }
    with args.report_output.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(counts, sort_keys=True))


if __name__ == '__main__':
    main()
