"""Package a prepared install-kit directory, preserving only public artifacts."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile

root, output = map(Path, sys.argv[1:3])
if not output.name.endswith('.tar.gz'):
    raise SystemExit('Output must end in .tar.gz')
name = output.name[:-len('.tar.gz')]
files = sorted(p for p in root.rglob('*') if p.is_file() and p != root / 'SHA256SUMS')
hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(root / 'SHA256SUMS').write_text(''.join('{}  {}\n'.format(v, k) for k, v in hashes.items()), encoding='utf-8', newline='\n')


def normalize(info):
    info.uid = info.gid = 0
    info.uname = info.gname = 'root'
    info.mode = 0o755 if info.isdir() or info.name.endswith('.sh') else 0o644
    return info


with tarfile.open(output, 'w:gz', compresslevel=6) as archive:
    archive.add(root, arcname=name, filter=normalize)
archive_hash = hashlib.sha256(output.read_bytes()).hexdigest()
output.with_name(output.name + '.sha256').write_text('{}  {}\n'.format(archive_hash, output.name), encoding='ascii', newline='\n')
seen = set()
with tarfile.open(output, 'r:gz') as archive:
    for member in archive:
        if not member.isfile():
            continue
        relative = member.name[len(name) + 1:]
        if relative == 'SHA256SUMS':
            continue
        assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == hashes[relative], relative
        seen.add(relative)
assert seen == set(hashes)
print(json.dumps({'archive': str(output), 'bytes': output.stat().st_size,
                  'sha256': archive_hash, 'verified_files': len(seen)}, indent=2))
