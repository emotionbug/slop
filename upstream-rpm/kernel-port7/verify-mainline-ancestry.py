#!/usr/bin/env python3
"""Resolve context-drift CVEs by checking fix ancestry against a Linux tag."""
import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.request


COMPARE_URL = 'https://api.github.com/repos/torvalds/linux/compare/{commit}...{tag}'


def compare(commit, tag):
    url = COMPARE_URL.format(commit=commit, tag=tag)
    headers = {'User-Agent': 'linuxoss-cve-source-verifier/1.0',
               'Accept': 'application/vnd.github+json'}
    if token := os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        return {'commit': commit, 'url': url, 'http_status': error.code,
                'is_ancestor': False}
    return {'commit': commit, 'url': url, 'http_status': 200,
            'status': data['status'], 'ahead_by': data['ahead_by'],
            'behind_by': data['behind_by'],
            'is_ancestor': (data['status'] in ('ahead', 'identical')
                            and data['behind_by'] == 0)}


def resolved_status(patch_status, ancestry):
    if patch_status == 'fix-present-exact-reverse-apply':
        return 'fix-present-exact-reverse-apply'
    if any(item['is_ancestor'] and item['evidence_kind'] == 'vulnerable-code-removed'
           for item in ancestry):
        return 'not-affected-code-removed-in-base-tag'
    if any(item['is_ancestor'] and item['evidence_kind'] == 'fix-commit'
           for item in ancestry):
        return 'fix-present-in-base-tag-ancestry'
    return patch_status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patch-results', type=Path, required=True)
    parser.add_argument('--tag', default='v7.2')
    parser.add_argument('--comparison-cache', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.patch_results.read_text(encoding='utf-8'))
    cache = {}
    if args.comparison_cache:
        prior = json.loads(args.comparison_cache.read_text(encoding='utf-8'))
        for old_item in prior.get('items', []):
            for check in old_item.get('ancestry_checks', []):
                if check.get('http_status') == 200:
                    cache[check['commit']] = {
                        key: value for key, value in check.items()
                        if key != 'evidence_kind'
                    }
    results = []
    for item in source['items']:
        candidates = {(check['upstream_commit'], 'fix-commit')
                      for check in item['patch_checks']}
        candidates.update((check['upstream_removed_by'], 'vulnerable-code-removed')
                          for check in item['patch_checks']
                          if check['upstream_removed_by'])
        ancestry = []
        if item['status'] != 'fix-present-exact-reverse-apply':
            for commit, kind in sorted(candidates):
                if commit not in cache:
                    cache[commit] = compare(commit, args.tag)
                ancestry.append(dict(cache[commit], evidence_kind=kind))
        result = dict(item)
        result['base_tag'] = args.tag
        result['ancestry_checks'] = ancestry
        result['resolved_status'] = resolved_status(item['status'], ancestry)
        results.append(result)
        print(item['cve'], result['resolved_status'], flush=True)
    counts = {}
    for result in results:
        status = result['resolved_status']
        counts[status] = counts.get(status, 0) + 1
    output = {
        'schema_version': 1,
        'scope': ('Exact patch-content checks plus mainline fix ancestry to the '
                  'base tag; not a runtime exploit test.'),
        'candidate': source['candidate'],
        'source_sha256': source['source_sha256'],
        'base_tag': args.tag,
        'linux_cna_commit': source['linux_cna_commit'],
        'counts': counts,
        'items': results,
    }
    args.output.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8',
                           newline='\n')


if __name__ == '__main__':
    main()
