#!/usr/bin/env python3
"""Conservatively compare changed patch lines with a downstream source tree."""
import argparse
import hashlib
import json
from pathlib import Path
import re


DIFF = re.compile(r'^diff --git a/(\S+) b/(\S+)$')
HUNK = re.compile(r'^@@ ')


def substantive(line):
    value = line.strip()
    if len(value) < 12:
        return False
    if value in ('/*', '*/') or value.startswith('//'):
        return False
    if value.startswith('*') and not any(char in value for char in '();='):
        return False
    return True


def patch_hunks(data):
    current_file = None
    current_hunk = None
    hunks = []
    for line in data.decode(errors='replace').splitlines():
        match = DIFF.match(line)
        if match:
            current_file = match.group(2)
            current_hunk = None
        elif current_file and HUNK.match(line):
            current_hunk = {'file': current_file, 'added': [], 'removed': []}
            hunks.append(current_hunk)
        elif current_hunk is not None and line.startswith('+') and not line.startswith('+++'):
            if substantive(line[1:]):
                current_hunk['added'].append(line[1:].strip())
        elif current_hunk is not None and line.startswith('-') and not line.startswith('---'):
            if substantive(line[1:]):
                current_hunk['removed'].append(line[1:].strip())
    return hunks


def analyze_patch(source, data):
    details = []
    fixed = True
    vulnerable = True
    evidence_lines = 0
    for hunk in patch_hunks(data):
        path = source / hunk['file']
        if not path.is_file():
            fixed = vulnerable = False
            details.append({'file': hunk['file'], 'status': 'file-absent'})
            continue
        source_lines = {line.strip() for line in path.read_text(
            encoding='utf-8', errors='replace').splitlines()}
        added = set(hunk['added']) - set(hunk['removed'])
        removed = set(hunk['removed']) - set(hunk['added'])
        if not added and not removed:
            continue
        evidence_lines += len(added) + len(removed)
        added_present = sorted(added & source_lines)
        removed_present = sorted(removed & source_lines)
        hunk_fixed = bool(added) and added == set(added_present) and not removed_present
        hunk_vulnerable = (bool(removed) and removed == set(removed_present)
                           and not added_present)
        fixed = fixed and hunk_fixed
        vulnerable = vulnerable and hunk_vulnerable
        details.append({
            'file': hunk['file'],
            'added_distinctive': len(added),
            'added_present': len(added_present),
            'removed_distinctive': len(removed),
            'removed_present': len(removed_present),
            'status': ('fix-lines-present' if hunk_fixed else
                       'old-lines-present' if hunk_vulnerable else 'mixed'),
        })
    if evidence_lines < 2 or not details:
        status = 'insufficient-distinctive-lines'
    elif fixed:
        status = 'semantic-fix-lines-present'
    elif vulnerable:
        status = 'semantic-old-lines-present'
    else:
        status = 'mixed-or-diverged'
    return {'status': status, 'evidence_lines': evidence_lines, 'hunks': details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checks', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    check_bytes = args.checks.read_bytes()
    checks = json.loads(check_bytes)
    items = []
    counts = {}
    for item in checks['items']:
        if item['status'] != 'inconclusive-context-drift':
            continue
        variants = []
        for check in item['patch_checks']:
            patch = args.cache / (check['commit'] + '.patch')
            data = patch.read_bytes()
            if hashlib.sha256(data).hexdigest() != check['patch_sha256']:
                raise ValueError(item['cve'] + ': patch hash mismatch')
            result = analyze_patch(args.source, data)
            result['commit'] = check['commit']
            result['patch_sha256'] = check['patch_sha256']
            variants.append(result)
        statuses = {variant['status'] for variant in variants}
        if 'semantic-fix-lines-present' in statuses:
            status = 'semantic-fix-lines-present'
        elif 'semantic-old-lines-present' in statuses:
            status = 'semantic-old-lines-present'
        else:
            status = 'manual-review-required'
        counts[status] = counts.get(status, 0) + 1
        result = dict(item)
        result['semantic_status'] = status
        result['variants'] = variants
        items.append(result)
    output = {
        'schema_version': 1,
        'scope': ('Exact distinctive-line comparison for patches that could not '
                  'be applied in either direction. Only semantic-fix-lines-present '
                  'is positive fix evidence; other results require review.'),
        'checks_sha256': hashlib.sha256(check_bytes).hexdigest(),
        'counts': counts,
        'items': items,
    }
    with args.output.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(output, indent=2) + '\n')
    print(json.dumps(counts, sort_keys=True))


if __name__ == '__main__':
    main()
