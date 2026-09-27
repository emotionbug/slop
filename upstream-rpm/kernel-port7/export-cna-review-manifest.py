#!/usr/bin/env python3
"""Export pinned Linux CNA fix commits for unresolved crosswalk rows."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess


SHA = re.compile(r'^[0-9a-f]{40}$')


def git_head(repo):
    return subprocess.check_output(
        ['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()


def git_show_many(repo, object_names):
    process = subprocess.Popen(
        ['git', '-C', str(repo), 'cat-file', '--batch'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    request = ''.join(name + '\n' for name in object_names).encode()
    output, _ = process.communicate(request)
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, process.args)
    stream = io.BytesIO(output)
    values = {}
    for name in object_names:
        header = stream.readline().decode().strip().split()
        if len(header) != 3 or header[1] != 'blob':
            raise ValueError('{}: unavailable Git blob: {}'.format(name, header))
        size = int(header[2])
        values[name] = stream.read(size).decode()
        if stream.read(1) != b'\n':
            raise ValueError(name + ': malformed git cat-file response')
    return values


def fix_commits(record):
    commits = []
    seen = set()
    for product in record.get('containers', {}).get('cna', {}).get('affected', []):
        if product.get('vendor') != 'Linux' or product.get('product') != 'Linux':
            continue
        for rule in product.get('versions', []):
            commit = rule.get('lessThan')
            if (rule.get('versionType') == 'git' and rule.get('status') == 'affected'
                    and isinstance(commit, str) and SHA.fullmatch(commit)):
                if commit not in seen:
                    commits.append(commit)
                    seen.add(commit)
    return commits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crosswalk', type=Path, required=True)
    parser.add_argument('--cna-git', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--statuses', default='needs-review',
                        help='Comma-separated crosswalk statuses to export')
    args = parser.parse_args()
    statuses = {status.strip() for status in args.statuses.split(',') if status.strip()}
    if not statuses:
        parser.error('--statuses must name at least one status')
    crosswalk = json.loads(args.crosswalk.read_text(encoding='utf-8'))
    pinned = crosswalk['linux_cna_commit']
    if git_head(args.cna_git) != pinned:
        raise ValueError('Linux CNA checkout does not match pinned commit ' + pinned)
    selected = [item for item in crosswalk['items'] if item['status'] in statuses]
    object_names = []
    for item in selected:
        commit, path = item['record_path'].split(':', 1)
        if commit != pinned:
            raise ValueError(f"{item['cve']}: record is not pinned to {pinned}")
        object_names.append('{}:{}'.format(commit, path))
    records = git_show_many(args.cna_git, object_names)
    items = []
    for item, object_name in zip(selected, object_names):
        path = object_name.split(':', 1)[1]
        raw = records[object_name]
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
        'statuses': sorted(statuses),
        'items': items,
    }
    args.output.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8',
                           newline='\n')


if __name__ == '__main__':
    main()
