#!/usr/bin/env python3
"""Merge exact kernel identities and stage the host installer (before WASM packaging)."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

bundle, extension, native, kit = (Path(p).resolve() for p in sys.argv[1:5])
extra = json.loads(extension.read_text(encoding='utf-8'))
catalog_path = native / 'catalog.json'
catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
identities = {p['rpm_sha256'] for p in catalog['artifacts']}
catalog['artifacts'].extend(p for p in extra['artifacts'] if p['rpm_sha256'] not in identities)
catalog['source_projects_sha256'] = extra['source_projects_sha256']
record = {'release': 'linuxoss-kernel-20260925-1', 'sha256': extra['bundle_manifest_sha256']}
if record not in catalog['extension_manifests']:
    catalog['extension_manifests'].append(record)
with catalog_path.open('w', encoding='utf-8', newline='\n') as f:
    json.dump(catalog, f, indent=2, sort_keys=True); f.write('\n')
kit.mkdir(exist_ok=False)
(kit / 'rpms').mkdir()
recipe = Path(__file__).resolve().parent
for name in ('kernel.sh', 'kernel.py', 'README-ko.md'):
    shutil.copyfile(recipe / name, kit / name)
shutil.copyfile(recipe.parent / 'deploy/scan.sh', kit / 'scan.sh')
core = next(p for p in extra['artifacts'] if p['name'] == 'kernel')
manifest = {'schema_version': 1, 'kernel_release': '7.2.7-linuxoss+',
            'kernel_image_sha256': core['files']['/lib/modules/7.2.7-linuxoss+/vmlinuz'],
            'rpms': [], 'source_release': 'https://github.com/emotionbug/slop/releases/tag/linuxoss-kernel-20260925-1',
            'source_rpm': core['sourcerpm'], 'source_rpm_sha256': core['srpm_sha256'],
            'source_signature': 'Official Linux 7.2.7 source signature verified in the original source intake; pinned release source reused.',
            'scope': 'Add kernel and matching kernel-devel alongside existing kernels; /usr/include headers remain unchanged.'}
for p in extra['artifacts']:
    if p['name'] not in ('kernel', 'kernel-devel'):
        continue
    name = p['name'] + '-' + p['version'] + '-' + p['release'] + '.' + p['arch'] + '.rpm'
    src = bundle / 'rpms' / name
    if hashlib.sha256(src.read_bytes()).hexdigest() != p['rpm_sha256']:
        raise ValueError('RPM changed after catalog creation: ' + name)
    shutil.copyfile(src, kit / 'rpms' / name)
    manifest['rpms'].append({'path': 'rpms/' + name, 'name': p['name'], 'sha256': p['rpm_sha256'],
                             'size': src.stat().st_size, 'srpm_sha256': p['srpm_sha256']})
with (kit / 'kernel-manifest.json').open('w', encoding='utf-8', newline='\n') as f:
    json.dump(manifest, f, indent=2); f.write('\n')
print(json.dumps({'catalog_artifacts': len(catalog['artifacts']), 'manifest': manifest}, indent=2))
