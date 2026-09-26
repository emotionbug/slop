#!/usr/bin/env python3
"""Check official Linux stable fix patches against an extracted source tree."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request


PATCH_URL = ('https://git.kernel.org/pub/scm/linux/kernel/git/stable/'
             'linux.git/patch/?id={commit}')
UPSTREAM = re.compile(rb'(?m)^commit ([0-9a-f]{40}) upstream\.$')
REMOVED_BY = re.compile(
    rb'code was removed by upstream\s+commit ([0-9a-f]{12,40})', re.MULTILINE)


def download(commit, cache):
    path = cache / f'{commit}.patch'
    if not path.exists():
        request = urllib.request.Request(
            PATCH_URL.format(commit=commit),
            headers={'User-Agent': 'linuxoss-cve-source-verifier/1.0'})
        data = urllib.request.urlopen(request, timeout=60).read()
        if not data.startswith(f'From {commit} '.encode()):
            raise ValueError(f'{commit}: response is not the requested patch')
        path.write_bytes(data)
    return path


def apply_check(source, patch, reverse=False):
    command = ['git', 'apply', '--check', '--recount']
    if reverse:
        command.append('--reverse')
    command.append(str(patch))
    result = subprocess.run(command, cwd=source, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return {'applies': result.returncode == 0,
            'diagnostic': result.stdout.strip()[:1000]}


def classify(checks):
    if any(check['reverse']['applies'] for check in checks):
        return 'fix-present-exact-reverse-apply'
    if any(check['forward']['applies'] for check in checks):
        return 'fix-absent-forward-apply'
    return 'inconclusive-context-drift'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{64}', args.source_sha256):
        parser.error('--source-sha256 must be 64 lowercase hexadecimal characters')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    args.cache.mkdir(parents=True, exist_ok=True)
    results = []
    for item in manifest['items']:
        checks = []
        for commit in item['fix_commits']:
            patch = download(commit, args.cache)
            patch_bytes = patch.read_bytes()
            reverse = apply_check(args.source, patch, reverse=True)
            forward = ({'applies': False, 'diagnostic': 'skipped: reverse applies'}
                       if reverse['applies'] else apply_check(args.source, patch))
            checks.append({
                'commit': commit,
                'upstream_commit': ((match.group(1).decode() if (match := UPSTREAM.search(
                    patch_bytes)) else commit)),
                'upstream_removed_by': ((match.group(1).decode() if (match :=
                    REMOVED_BY.search(patch_bytes)) else None)),
                'url': PATCH_URL.format(commit=commit),
                'patch_sha256': hashlib.sha256(patch_bytes).hexdigest(),
                'reverse': reverse,
                'forward': forward,
            })
        result = dict(item)
        result['status'] = classify(checks)
        result['patch_checks'] = checks
        results.append(result)
        print(item['cve'], result['status'], flush=True)
    counts = {}
    for result in results:
        counts[result['status']] = counts.get(result['status'], 0) + 1
    output = {
        'schema_version': 1,
        'scope': ('Patch-content check of extracted source; exact reverse apply is '
                  'strong fix-presence evidence, but not a runtime exploit test.'),
        'candidate': manifest['candidate'],
        'source_sha256': args.source_sha256,
        'linux_cna_commit': manifest['linux_cna_commit'],
        'counts': counts,
        'items': results,
    }
    args.output.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8',
                           newline='\n')


if __name__ == '__main__':
    main()
