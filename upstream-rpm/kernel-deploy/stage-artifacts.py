#!/usr/bin/env python3
"""Stage the completed release-3 RPMs and pin their source mapping, before cataloging."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

build, stage, native = (Path(p).resolve() for p in sys.argv[1:4])
if (build / 'build-exit-code.txt').read_text().strip() != '0':
    raise SystemExit('Kernel build did not complete successfully')
config = (build / 'config-after').read_text()
for option in ('CONFIG_MEMCG_V1=y', 'CONFIG_DEBUG_INFO_BTF=y', 'CONFIG_DEBUG_INFO_COMPRESSED_ZLIB=y'):
    if option not in config.splitlines():
        raise SystemExit('Required configuration missing: ' + option)
stage.mkdir(exist_ok=False)
files = []
for name in ('kernel', 'kernel-devel', 'kernel-headers'):
    path = build / (name + '-7.2.7_linuxoss+-3.el8.x86_64.rpm')
    dest = stage / 'rpms' / path.name
    dest.parent.mkdir(exist_ok=True)
    shutil.copyfile(path, dest)
    files.append({'path': dest.relative_to(stage).as_posix(), 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(), 'bytes': dest.stat().st_size})
path = build / 'kernel-7.2.7_linuxoss+-3.el8.src.rpm'
dest = stage / 'srpms' / path.name
dest.parent.mkdir(exist_ok=True)
shutil.copyfile(path, dest)
source_hash = hashlib.sha256(dest.read_bytes()).hexdigest()
files.append({'path': dest.relative_to(stage).as_posix(), 'sha256': source_hash, 'bytes': dest.stat().st_size})
manifest = {'schema_version': 1, 'release': 'linuxoss-kernel-20260925-1', 'files': files}
with (stage / 'manifest.json').open('w', encoding='utf-8', newline='\n') as f:
    json.dump(manifest, f, indent=2); f.write('\n')
mapping_path = native / 'source-projects.json'
mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
mapping['artifacts'][source_hash] = {
    'project': 'kernel', 'include_nonstandard_vendor': True,
    'components': [{'project': 'kernel', 'version': '7.2.7'}],
    'evidence': 'Hash-verified Linux 7.2.7 source; release 3 restores EL8 cgroup v1 memory controller and preserves BTF. RPM version suffix is packaging identity, not an upstream version.'}
with mapping_path.open('w', encoding='utf-8', newline='\n') as f:
    json.dump(mapping, f, indent=2); f.write('\n')
print(json.dumps(manifest, indent=2))
