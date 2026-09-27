#!/usr/bin/env python3
"""Check official Linux stable fix patches against an extracted source tree."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from urllib.error import HTTPError, URLError
import urllib.request


PATCH_URL = ('https://git.kernel.org/pub/scm/linux/kernel/git/stable/'
             'linux.git/patch/?id={commit}')
PATCH_MIRROR_URL = 'https://github.com/gregkh/linux/commit/{commit}.patch'
UPSTREAM = re.compile(rb'(?m)^commit ([0-9a-f]{40}) upstream\.$')
REMOVED_BY = re.compile(
    rb'code was removed by upstream\s+commit ([0-9a-f]{12,40})', re.MULTILINE)


def download(commit, cache, attempts=3):
    path = cache / f'{commit}.patch'
    url_path = cache / f'{commit}.url'
    if not path.exists():
        last_error = None
        for template in (PATCH_URL, PATCH_MIRROR_URL):
            url = template.format(commit=commit)
            request = urllib.request.Request(
                url, headers={'User-Agent': 'linuxoss-cve-source-verifier/1.0'})
            for attempt in range(attempts):
                try:
                    data = urllib.request.urlopen(request, timeout=60).read()
                    last_error = None
                    break
                except HTTPError as error:
                    last_error = error
                    if error.code not in (429, 500, 502, 503, 504):
                        break
                except URLError as error:
                    last_error = error
                time.sleep(min(10, 2 ** attempt))
            if last_error is None:
                break
        if last_error is not None:
            raise last_error
        if not data.startswith(f'From {commit} '.encode()):
            raise ValueError(f'{commit}: response is not the requested patch')
        temporary = cache / '{}.{}.{}.tmp'.format(
            commit, os.getpid(), threading.get_ident())
        temporary.write_bytes(data)
        os.replace(str(temporary), str(path))
        url_path.write_text(url + '\n', encoding='utf-8')
    url = (url_path.read_text(encoding='utf-8').strip()
           if url_path.exists() else PATCH_URL.format(commit=commit))
    return path, url


def apply_check(source, patch, reverse=False):
    if shutil.which('git'):
        command = ['git', 'apply', '--check', '--recount']
        if reverse:
            command.append('--reverse')
        command.append(str(patch))
        engine = 'git-apply-check'
    else:
        # GNU patch otherwise permits fuzz by default, which is not an exact
        # source-content check and made the status name overstate the evidence.
        command = ['patch', '-p1', '--dry-run', '--batch', '--fuzz=0',
                   '--forward']
        if reverse:
            command.append('--reverse')
        command.extend(['--input', str(patch)])
        engine = 'gnu-patch-dry-run'
    result = subprocess.run(command, cwd=source, universal_newlines=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return {'applies': result.returncode == 0,
            'engine': engine,
            'diagnostic': result.stdout.strip()[:1000]}


def classify(checks):
    if any(check['reverse']['applies'] for check in checks):
        return 'fix-present-exact-reverse-apply'
    if any(check['forward']['applies'] for check in checks):
        return 'fix-absent-forward-apply'
    return 'inconclusive-context-drift'


def check_item(item, source, cache, stop_on_decision):
    checks = []
    for commit in item['fix_commits']:
        patch, patch_url = download(commit, cache)
        patch_bytes = patch.read_bytes()
        reverse = apply_check(source, patch, reverse=True)
        forward = ({'applies': False, 'diagnostic': 'skipped: reverse applies'}
                   if reverse['applies'] else apply_check(source, patch))
        match = UPSTREAM.search(patch_bytes)
        upstream_commit = match.group(1).decode() if match else commit
        match = REMOVED_BY.search(patch_bytes)
        upstream_removed_by = match.group(1).decode() if match else None
        checks.append({
            'commit': commit,
            'upstream_commit': upstream_commit,
            'upstream_removed_by': upstream_removed_by,
            'url': patch_url,
            'patch_sha256': hashlib.sha256(patch_bytes).hexdigest(),
            'reverse': reverse,
            'forward': forward,
        })
        if stop_on_decision and (reverse['applies'] or forward['applies']):
            break
    result = dict(item)
    result['status'] = classify(checks)
    result['patch_checks'] = checks
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--stop-on-decision', action='store_true')
    parser.add_argument('--input-statuses', default='',
                        help=('Optional comma-separated statuses already present '
                              'on input items; only matching items are checked'))
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{64}', args.source_sha256):
        parser.error('--source-sha256 must be 64 lowercase hexadecimal characters')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    args.cache.mkdir(parents=True, exist_ok=True)
    if args.workers < 1:
        parser.error('--workers must be positive')
    selected = manifest['items']
    if args.input_statuses:
        input_statuses = {value.strip() for value in
                          args.input_statuses.split(',') if value.strip()}
        selected = [item for item in selected
                    if item.get('status') in input_statuses]
    ordered = [None] * len(selected)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(check_item, item, args.source, args.cache,
                            args.stop_on_decision): index
            for index, item in enumerate(selected)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                result = future.result()
            except Exception as error:
                result = dict(selected[index])
                result['status'] = 'verification-error'
                result['patch_checks'] = []
                result['error'] = '{}: {}'.format(type(error).__name__, error)
            ordered[index] = result
            print(result['cve'], result['status'], flush=True)
    results = ordered
    counts = {}
    for result in results:
        counts[result['status']] = counts.get(result['status'], 0) + 1
    output = {
        'schema_version': 1,
        'scope': ('Patch-content check of extracted source; exact reverse apply is '
                  'strong fix-presence evidence, but not a runtime exploit test.'),
        'candidate': manifest['candidate'],
        'source_sha256': args.source_sha256,
        'linux_cna_commit': manifest.get('linux_cna_commit'),
        'cvelist_commit': manifest.get('cvelist_commit'),
        'counts': counts,
        'items': results,
    }
    with args.output.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()
