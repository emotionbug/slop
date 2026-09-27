#!/usr/bin/env python3
"""Refresh selected CVE files after a Red Hat weekly VEX archive snapshot."""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import urllib.request


BASE = 'https://security.access.redhat.com/data/csaf/v2/vex/'


def cves_from_document(path):
    document = json.loads(path.read_text(encoding='utf-8'))
    return {item['cve'].lower() for item in document['items']}


def download(base, relative, root):
    destination = root / relative
    request = urllib.request.Request(
        base.rstrip('/') + '/' + relative,
        headers={'User-Agent': 'linuxoss-redhat-vex-refresh/1.0'})
    data = urllib.request.urlopen(request, timeout=120).read()
    document = json.loads(data)
    expected = Path(relative).stem.upper()
    actual = document.get('document', {}).get('tracking', {}).get('id', '').upper()
    if actual != expected:
        raise ValueError('{}: tracking id {} != {}'.format(relative, actual, expected))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        destination.name + '.{}.tmp'.format(os.getpid()))
    temporary.write_bytes(data)
    os.replace(str(temporary), str(destination))
    return relative, hashlib.sha256(data).hexdigest(), len(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--changes', type=Path, required=True)
    parser.add_argument('--since', required=True,
                        help='ISO timestamp of the extracted weekly archive')
    parser.add_argument('--cves', type=Path, required=True,
                        help='Crosswalk JSON whose items contain cve fields')
    parser.add_argument('--vex-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base-url', default=BASE)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    since = args.since.replace('Z', '+00:00')
    selected_cves = cves_from_document(args.cves)
    paths = []
    with args.changes.open(encoding='utf-8', newline='') as stream:
        for relative, changed in csv.reader(stream):
            # Red Hat publishes normalized, zero-padded ISO-8601 UTC timestamps,
            # so lexical order is chronological and works on EL8 Python 3.6.
            if changed <= since:
                continue
            if Path(relative).stem.lower() in selected_cves:
                paths.append(relative)
    paths = sorted(set(paths))
    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download, args.base_url, path,
                                   args.vex_root): path for path in paths}
        for future in as_completed(futures):
            try:
                relative, sha256, size = future.result()
                results.append({'path': relative, 'sha256': sha256, 'size': size})
            except Exception as error:
                errors.append({'path': futures[future],
                               'error': '{}: {}'.format(type(error).__name__, error)})
    report = {
        'schema_version': 1,
        'archive_cutoff': args.since,
        'changes_sha256': hashlib.sha256(args.changes.read_bytes()).hexdigest(),
        'selected': len(paths),
        'updated': len(results),
        'errors': errors,
        'files': sorted(results, key=lambda item: item['path']),
    }
    with args.output.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('selected', 'updated')},
                     sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
