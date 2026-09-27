#!/usr/bin/env python3
"""Atomically complete official Linux stable fixes one patch hunk at a time.

Downstream kernels often contain most of a stable fix while later vendor edits
make a whole-patch reverse check fail.  This tool splits each official patch
into individual textual hunks, evaluates them in a temporary copy of only the
files touched by that patch, and accepts a CVE only when every hunk is either
already present or can be applied with the configured bounded fuzz.  A failed
hunk discards all tentative changes for that CVE.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


DIFF = re.compile(br'^diff --git a/(.+) b/(.+)$')


def run_patch(root, payload, reverse=False, fuzz=0, dry_run=True):
    command = ['patch', '-p1', '--batch', '--fuzz={}'.format(fuzz)]
    command.append('--reverse' if reverse else '--forward')
    if dry_run:
        command.append('--dry-run')
    result = subprocess.run(command, cwd=str(root), input=payload,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.returncode, result.stdout.decode('utf-8', 'replace').strip()


def split_hunks(data):
    """Return [(path, complete-one-hunk-patch)] for ordinary unified diffs."""
    lines = data.splitlines(keepends=True)
    sections = []
    start = None
    for index, line in enumerate(lines):
        if line.startswith(b'diff --git '):
            if start is not None:
                sections.append(lines[start:index])
            start = index
    if start is not None:
        sections.append(lines[start:])
    output = []
    for section in sections:
        match = DIFF.match(section[0].rstrip(b'\r\n'))
        if not match or match.group(1) != match.group(2):
            return []
        path = match.group(1).decode('utf-8', 'surrogateescape')
        hunk_starts = [i for i, line in enumerate(section)
                       if line.startswith(b'@@ ')]
        if not hunk_starts:
            return []
        header = section[:hunk_starts[0]]
        for pos, hunk_start in enumerate(hunk_starts):
            end = hunk_starts[pos + 1] if pos + 1 < len(hunk_starts) else len(section)
            output.append((path, b''.join(header + section[hunk_start:end])))
    return output


def touched_files(hunks):
    return sorted(set(path for path, _ in hunks))


def seed_tree(source, destination, paths):
    for relative in paths:
        original = source / relative
        if not original.is_file():
            return False, 'missing source file: ' + relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(original), str(target))
    return True, ''


def evaluate_hunks(root, hunks, fuzz, apply):
    actions = []
    for number, (path, payload) in enumerate(hunks, 1):
        reverse_rc, reverse_out = run_patch(
            root, payload, reverse=True, fuzz=0, dry_run=True)
        if reverse_rc == 0:
            actions.append({'hunk': number, 'path': path,
                            'action': 'already-present-exact',
                            'diagnostic': reverse_out[:1200]})
            continue
        if fuzz:
            fuzzy_rc, fuzzy_out = run_patch(
                root, payload, reverse=True, fuzz=fuzz, dry_run=True)
            if fuzzy_rc == 0:
                actions.append({
                    'hunk': number, 'path': path,
                    'action': 'already-present-fuzzy-{}'.format(fuzz),
                    'diagnostic': fuzzy_out[:1200],
                })
                continue
        forward_rc, forward_out = run_patch(
            root, payload, reverse=False, fuzz=0, dry_run=True)
        used_fuzz = 0
        if forward_rc and fuzz:
            forward_rc, forward_out = run_patch(
                root, payload, reverse=False, fuzz=fuzz, dry_run=True)
            used_fuzz = fuzz
        if forward_rc:
            return False, actions, {
                'hunk': number, 'path': path,
                'reverse': reverse_out[:1600],
                'forward': forward_out[:1600],
            }
        if apply:
            apply_rc, apply_out = run_patch(
                root, payload, reverse=False, fuzz=used_fuzz, dry_run=False)
            if apply_rc:
                raise RuntimeError('{} hunk {} changed after dry-run: {}'.format(
                    path, number, apply_out))
        actions.append({'hunk': number, 'path': path,
                        'action': ('applied-exact' if used_fuzz == 0
                                   else 'applied-fuzzy-{}'.format(used_fuzz)),
                        'diagnostic': forward_out[:1200]})
    return True, actions, None


def evaluate_candidate(source, cache, check, fuzz):
    patch_path = cache / (check['commit'] + '.patch')
    data = patch_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != check['patch_sha256']:
        raise ValueError('{}: cached patch hash mismatch'.format(check['commit']))
    hunks = split_hunks(data)
    if not hunks:
        return {'status': 'unsupported-patch-shape', 'commit': check['commit']}
    with tempfile.TemporaryDirectory(prefix='cna-hunks.') as temporary:
        root = Path(temporary)
        seeded, reason = seed_tree(source, root, touched_files(hunks))
        if not seeded:
            return {'status': 'not-applicable', 'commit': check['commit'],
                    'reason': reason}
        complete, actions, failed = evaluate_hunks(root, hunks, fuzz, apply=True)
        if not complete:
            return {'status': 'not-applicable', 'commit': check['commit'],
                    'hunk_count': len(hunks), 'accounted_hunks': len(actions),
                    'failed': failed}
        changed = sum(action['action'].startswith('applied-') for action in actions)
        fuzzy = sum('fuzzy-' in action['action'] for action in actions)
        return {'status': 'complete', 'commit': check['commit'],
                'patch_sha256': actual, 'hunk_count': len(hunks),
                'changed_hunks': changed, 'fuzzy_hunks': fuzzy,
                'actions': actions}


def apply_candidate(source, cache, candidate, fuzz):
    data = (cache / (candidate['commit'] + '.patch')).read_bytes()
    hunks = split_hunks(data)
    complete, actions, failed = evaluate_hunks(source, hunks, fuzz, apply=True)
    if not complete:
        raise RuntimeError('{} became inapplicable: {}'.format(
            candidate['commit'], failed))
    return actions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checks', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fuzz', type=int, default=2)
    parser.add_argument('--check-only', action='store_true',
                        help='Report applicable missing hunks without changing source')
    args = parser.parse_args()
    if args.fuzz < 0 or args.fuzz > 2:
        parser.error('--fuzz must be between 0 and 2')
    checks = json.loads(args.checks.read_text(encoding='utf-8'))
    selected = [item for item in checks['items'] if item['status'] in {
        'inconclusive-context-drift', 'fix-absent-forward-apply'}]
    results = []
    for item in selected:
        candidates = []
        for check in item['patch_checks']:
            candidate = evaluate_candidate(args.source, args.cache, check, args.fuzz)
            candidates.append(candidate)
        complete = [candidate for candidate in candidates
                    if candidate['status'] == 'complete']
        if complete:
            # Prefer no source change, then the fewest fuzzy and total changed hunks.
            chosen = min(complete, key=lambda value: (
                value['changed_hunks'] != 0, value['fuzzy_hunks'],
                value['changed_hunks'], value['hunk_count']))
            actions = (chosen['actions'] if args.check_only else
                       apply_candidate(args.source, args.cache, chosen, args.fuzz))
            if chosen['changed_hunks'] == 0:
                status = ('already-present-by-hunks'
                          if chosen['fuzzy_hunks'] == 0
                          else 'already-present-by-fuzzy-hunks')
            else:
                status = ('applied-by-hunks'
                          if chosen['fuzzy_hunks'] == 0
                          else 'applied-by-fuzzy-hunks')
            result = {'cve': item['cve'], 'status': status,
                      'commit': chosen['commit'],
                      'patch_sha256': chosen['patch_sha256'],
                      'hunk_count': chosen['hunk_count'],
                      'changed_hunks': chosen['changed_hunks'],
                      'fuzzy_hunks': chosen['fuzzy_hunks'],
                      'actions': actions}
            print(item['cve'], status, chosen['commit'],
                  chosen['changed_hunks'], flush=True)
        else:
            ranked = sorted(candidates, key=lambda value: (
                -value.get('accounted_hunks', 0), value.get('hunk_count', 10 ** 9)))
            result = {'cve': item['cve'], 'status': 'manual-review-required',
                      'best_candidate': ranked[0] if ranked else None}
        results.append(result)
    counts = {}
    for result in results:
        counts[result['status']] = counts.get(result['status'], 0) + 1
    document = {
        'schema_version': 1,
        'scope': ('Official stable patch hunks; atomic per CVE; bounded GNU '
                  'patch fuzz; no partial CVE changes retained.'),
        'fuzz': args.fuzz,
        'check_only': args.check_only,
        'counts': counts,
        'items': results,
    }
    with args.output.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(document, indent=2) + '\n')
    print(json.dumps(counts, sort_keys=True))


if __name__ == '__main__':
    main()
