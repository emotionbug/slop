"""Create an unsigned, checksum-pinned kit tar for the disposable boot test."""
from pathlib import Path
import hashlib
import sys
import tarfile

kit, archive = (Path(p).resolve() for p in sys.argv[1:3])
files = sorted(p for p in kit.rglob('*') if p.is_file() and p != kit/'SHA256SUMS')
assert not any(p.is_symlink() for p in files)
with (kit/'SHA256SUMS').open('w', encoding='ascii', newline='\n') as f:
    for p in files:
        f.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(kit).as_posix()+'\n')
with tarfile.open(archive, 'w') as tar:
    for p in files+[kit/'SHA256SUMS']:
        info=tar.gettarinfo(str(p),arcname=p.relative_to(kit).as_posix())
        info.uid=info.gid=0
        info.uname=info.gname='root'
        info.mode=0o755 if p.suffix=='.sh' else 0o644
        with p.open('rb') as f:
            tar.addfile(info,f)
print(str(archive))
