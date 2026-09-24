#!/usr/bin/env python3
"""Package only public module sources/feed and the WASM binary. No server data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output-dir", type=Path, required=True, help="New directory; archive created beside it")
args = p.parse_args()
source = Path(__file__).resolve().parent
stage = args.output_dir.resolve()
stage.mkdir(parents=True, exist_ok=False)
names = ['build-catalog.py', 'catalog.json', 'collect-installed.py', 'go.mod', 'logic.go',
         'logic_test.go', 'wasm.go', 'report.py', 'scan-native.sh', 'README.md',
         'advisory.go', 'advisories.json', 'project-map.json', 'reviewed-evidence.json',
         'refresh-feed.py', 'package-bundle.py', 'build-integration.ps1', 'test_feed.py']
for name in names:
    shutil.copy2(source / name, stage / name)
(stage / 'modules').mkdir()
shutil.copy2(source / 'modules/linuxoss-artifact-evidence.wasm', stage / 'modules/linuxoss-artifact-evidence.wasm')
goroot = Path(subprocess.check_output(['go', 'env', 'GOROOT'], universal_newlines=True).strip())
shutil.copy2(goroot / 'LICENSE', stage / 'GO-LICENSE.txt')
hashes = [hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.relative_to(stage).as_posix()
          for path in sorted(stage.rglob('*')) if path.is_file()]
(stage / 'SHA256SUMS').write_text('\n'.join(hashes) + '\n', encoding='utf-8')
archive = stage.with_suffix('.tar.gz')
with archive.open('xb') as stream:
    with tarfile.open(fileobj=stream, mode='w:gz') as out:
        for path in sorted(stage.rglob('*')):
            if not path.is_file():
                continue
            info = out.gettarinfo(str(path), arcname=path.relative_to(stage).as_posix())
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            info.mode = 0o644
            with path.open('rb') as src:
                out.addfile(info, src)
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix(archive.suffix + '.sha256').write_text(digest + '  ' + archive.name + '\n', encoding='utf-8')
print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': digest, 'files': len(hashes)+1}))
