#!/usr/bin/env python3
"""Export Linux fix commits from pinned CVE List V5 records.

This complements the Linux CNA repository for older CVEs whose records were
assigned by another CNA.  Only references that explicitly point to a Linux
kernel commit are accepted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.error import HTTPError, URLError
import urllib.request


SHA = r'([0-9a-fA-F]{12,40})'
COMMIT_PATTERNS = [
    re.compile(r'https?://git\.kernel\.org/[^ ]*(?:[?&]id=|/commit/[^/]+/?)' + SHA),
    re.compile(r'https?://github\.com/(?:torvalds|gregkh)/linux/commit/' + SHA),
    re.compile(r'https?://kernel\.googlesource\.com/[^ ]*/\+/' + SHA),
    re.compile(r'https?://git\.kernel\.org/(?:tip|linus)/' + SHA),
]


def head(repo):
    value = subprocess.check_output(
        ['git', 'ls-remote', repo, 'HEAD'], universal_newlines=True).split()[0]
    if not re.fullmatch(r'[0-9a-f]{40}', value):
        raise ValueError('Unexpected CVE List HEAD: ' + value)
    return value


def record_path(cve):
    _, year, number = cve.split('-')
    bucket = str(int(number) // 1000) + 'xxx'
    return 'cves/{}/{}/{}.json'.format(year, bucket, cve)


def download(url, destination, attempts=4):
    if destination.is_file():
        return destination.read_bytes()
    request = urllib.request.Request(
        url, headers={'User-Agent': 'linuxoss-cvelist-verifier/1.0'})
    last = None
    for attempt in range(attempts):
        try:
            data = urllib.request.urlopen(request, timeout=60).read()
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix('.tmp')
            temporary.write_bytes(data)
            temporary.replace(destination)
            return data
        except (HTTPError, URLError) as error:
            last = error
            time.sleep(min(8, 2 ** attempt))
    raise last


def references(record):
    values = []
    containers = record.get('containers', {})
    for container in [containers.get('cna', {})] + containers.get('adp', []):
        for reference in container.get('references', []):
            url = reference.get('url')
            if isinstance(url, str):
                values.append(url)
    return sorted(set(values))


def resolve_short_commit(value):
    if len(value) == 40:
        return value
    url = ('https://git.kernel.org/pub/scm/linux/kernel/git/stable/'
           'linux.git/patch/?id=' + value)
    try:
        request = urllib.request.Request(
            url, headers={'User-Agent': 'linuxoss-cvelist-verifier/1.0'})
        data = urllib.request.urlopen(request, timeout=60).read(200)
    except (HTTPError, URLError):
        return None
    match = re.match(br'From ([0-9a-f]{40}) ', data)
    return match.group(1).decode() if match else None


def commits(urls):
    values = []
    for url in urls:
        for pattern in COMMIT_PATTERNS:
            match = pattern.search(url)
            if match:
                value = resolve_short_commit(match.groups()[-1].lower())
                if value is None:
                    continue
                if value not in values:
                    values.append(value)
    return values


def title(record):
    cna = record.get('containers', {}).get('cna', {})
    if cna.get('title'):
        return cna['title']
    for description in cna.get('descriptions', []):
        if description.get('lang') == 'en':
            return description.get('value', '')
    return ''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crosswalk', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repository', default='https://github.com/CVEProject/cvelistV5.git')
    parser.add_argument('--commit')
    args = parser.parse_args()
    commit = args.commit or head(args.repository)
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        parser.error('--commit must be a full SHA-1')
    crosswalk = json.loads(args.crosswalk.read_text(encoding='utf-8'))
    selected = [item for item in crosswalk['items']
                if item['status'] == 'missing-linux-cna-record']
    items = []
    for item in selected:
        cve = item['cve']
        relative = record_path(cve)
        url = ('https://raw.githubusercontent.com/CVEProject/cvelistV5/'
               + commit + '/' + relative)
        raw = download(url, args.cache / relative)
        record = json.loads(raw.decode('utf-8'))
        if record.get('cveMetadata', {}).get('cveId') != cve:
            raise ValueError(cve + ': record identity mismatch')
        urls = references(record)
        items.append({
            'cve': cve,
            'title': title(record),
            'record_path': relative,
            'record_sha256': hashlib.sha256(raw).hexdigest(),
            'program_files': [],
            'references': urls,
            'fix_commits': commits(urls),
        })
        print(cve, len(items[-1]['fix_commits']), flush=True)
    document = {
        'schema_version': 1,
        'candidate': crosswalk['candidate'],
        'cvelist_repository': args.repository,
        'cvelist_commit': commit,
        'items': items,
    }
    with args.output.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(document, indent=2) + '\n')
    print(json.dumps({
        'items': len(items),
        'with_fix_commits': sum(bool(item['fix_commits']) for item in items),
        'commit': commit,
    }, sort_keys=True))


if __name__ == '__main__':
    main()
