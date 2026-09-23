#!/usr/bin/env python3
"""Download only hash-pinned public sources. No source commands are executed."""
import hashlib
import json
import pathlib
import urllib.request
import argparse
import io
import tarfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--only', action='append', default=[])
parser.add_argument('--destination', type=pathlib.Path)
args = parser.parse_args()
root = pathlib.Path(__file__).resolve().parent
destination = args.destination or root/'sources'
destination.mkdir(exist_ok=True)
for source in json.loads((root/'sources.lock.json').read_text())['sources']:
    name = source['name']
    if args.only and name not in args.only:
        continue
    if pathlib.PurePosixPath(name).name != name or not source['url'].startswith('https://'):
        raise SystemExit('Invalid source name/URL')
    path = destination/name
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']:
        print('VERIFIED', name)
        continue
    request = urllib.request.Request(source['url'], headers={'User-Agent': 'linux-oss-rpm-builder'})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read()
    if 'archive_member' in source:
        if hashlib.sha256(data).hexdigest() != source['archive_sha256']:
            raise SystemExit('SOURCE ARCHIVE HASH MISMATCH: '+name)
        # Read one exact regular member without extracting paths to disk.
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            member = archive.getmember(source['archive_member'])
            if not member.isfile() or member.size > 16*1024*1024:
                raise SystemExit('Invalid source archive member: '+name)
            data = archive.extractfile(member).read()
    if hashlib.sha256(data).hexdigest() != source['sha256']:
        raise SystemExit('SOURCE HASH MISMATCH: '+name)
    temporary = path.with_suffix(path.suffix+'.partial')
    temporary.write_bytes(data)
    temporary.replace(path)
    print('FETCHED AND VERIFIED', name)
