#!/usr/bin/env bash
# One additional transaction and focused checks in a disposable EL8 container.
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
mkdir -p /results
python3 - <<'PY'
import json,pathlib,subprocess
from importlib.machinery import SourceFileLoader
elf=SourceFileLoader('elf','/recipe/check-elf-exports.py').load_module()
paths=['/usr/lib64/libsolv.so.1','/usr/lib64/libsolvext.so.1','/usr/lib64/libprotobuf-c.so.1']
pathlib.Path('/results/exports-before.json').write_text(json.dumps({p:elf.exports(p) for p in paths},indent=2))
packages=['coreutils','coreutils-common','libsolv','protobuf-c']
files={p:subprocess.check_output(['rpm','-ql',p]).decode().splitlines() for p in packages}
pathlib.Path('/results/files-before.json').write_text(json.dumps(files,indent=2))
PY
printf '\n# Configuration-preservation fixture\n' >> /etc/DIR_COLORS
cp /etc/DIR_COLORS /tmp/wave6-dir-colors-before
dnf -y --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=install_weak_deps=False --setopt=localpkg_gpgcheck=False install /candidates/*.rpm
dnf --disableplugin=subscription-manager --disablerepo='*' check
cmp /etc/DIR_COLORS /tmp/wave6-dir-colors-before
python3 - <<'PY'
import json,os,pathlib,subprocess
from importlib.machinery import SourceFileLoader
elf=SourceFileLoader('elf','/recipe/check-elf-exports.py').load_module()
before=json.loads(pathlib.Path('/results/exports-before.json').read_text())
diff=[{'library':p,'baseline_exports':len(s),'missing':sorted(set(s)-set(elf.exports(p)))} for p,s in before.items()]
pathlib.Path('/results/exports-after.json').write_text(json.dumps(diff,indent=2))
assert not any(r['missing'] for r in diff),diff
old=json.loads(pathlib.Path('/results/files-before.json').read_text())
removed=[]
for name,paths in old.items():
 for p in paths:
  if p.startswith(('/etc/','/usr/bin/','/usr/sbin/','/usr/libexec/')) and not os.path.lexists(p):removed.append(p)
assert not removed,removed
print('OLD_EXPORTS_AND_EXECUTABLE_CONFIG_PATHS_PRESERVED')
PY
python3 /recipe/validate-wave6-runtime.py
echo WAVE6_TRANSACTION_AND_RUNTIME_OK
