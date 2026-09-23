#!/usr/bin/env python3
"""Download only hash-pinned public sources. No source commands are executed."""
import hashlib
import json
import pathlib
import urllib.request

root = pathlib.Path(__file__).resolve().parent
destination = root/'sources'
destination.mkdir(exist_ok=True)
for source in json.loads((root/'sources.lock.json').read_text())['sources']:
    name = source['name']
    if pathlib.PurePosixPath(name).name != name or not source['url'].startswith('https://'):
        raise SystemExit('Invalid source name/URL')
    path = destination/name
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']:
        print('VERIFIED', name)
        continue
    request = urllib.request.Request(source['url'], headers={'User-Agent': 'linux-oss-rpm-builder'})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != source['sha256']:
        raise SystemExit('SOURCE HASH MISMATCH: '+name)
    temporary = path.with_suffix(path.suffix+'.partial')
    temporary.write_bytes(data)
    temporary.replace(path)
    print('FETCHED AND VERIFIED', name)
