#!/usr/bin/env python3
"""Export pinned Linux CNA fix commits for unresolved crosswalk rows."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


SHA = re.compile(r'^[0-9a-f]{40}$')


def git_show(repo, object_name):
    return subprocess.check_output(
        ['git', '-C', str(repo), 'show', object_name], text=True)


def fix_commits(record):
    commits = set()
    for product in record.get('containers', {}).get('cna', {}).get('affected', []):
        if product.get('vendor') != 'Linux' or product.get('product') != 'Linux':
            continue
        for rule in product.get('versions', []):
            commit = rule.get('lessThan')
            if (rule.get('versionType') == 'git' and rule.get('status') == 'affected'
                    and isinstance(commit, str) and SHA.fullmatch(commit)):
                commits.add(commit)
    return sorted(commits)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crosswalk', type=Path, required=True)
    parser.add_argument('--cna-git', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    crosswalk = json.loads(args.crosswalk.read_text(encoding='utf-8'))
    pinned = crosswalk['linux_cna_commit']
    items = []
    for item in crosswalk['items']:
        if item['status'] != 'needs-review':
            continue
        commit, path = item['record_path'].split(':', 1)
        if commit != pinned:
            raise ValueError(f"{item['cve']}: record is not pinned to {pinned}")
        raw = git_show(args.cna_git, f'{commit}:{path}')
        record = json.loads(raw)
        cna = record['containers']['cna']
        files = sorted({name for product in cna.get('affected', [])
                        for name in product.get('programFiles', [])})
        items.append({
            'cve': item['cve'],
            'title': cna.get('title', ''),
            'record_path': path,
            'record_sha256': hashlib.sha256(raw.encode()).hexdigest(),
            'program_files': files,
            'fix_commits': fix_commits(record),
        })
    output = {
        'schema_version': 1,
        'candidate': crosswalk['candidate'],
        'linux_cna_commit': pinned,
        'items': items,
    }
    args.output.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8',
                           newline='\n')


if __name__ == '__main__':
    main()
