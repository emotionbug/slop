#!/usr/bin/env bash
# Run only in an isolated container; /kit and /results are bind mounts.
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
bash -n /kit/install.sh /kit/scan.sh
/usr/libexec/platform-python - <<'PY'
from pathlib import Path
compile(Path('/kit/install-rpms.py').read_text(), 'install-rpms.py', 'exec')
PY
finish() { cp -a /var/log/linuxoss-install/. /results/ 2>/dev/null || true; }
trap finish EXIT
rpm -qa | sort > /results/before.txt
bash /kit/install.sh check
rpm -qa | sort > /results/after-check.txt
/usr/libexec/platform-python - <<'PY'
from pathlib import Path
assert Path('/results/before.txt').read_bytes() == Path('/results/after-check.txt').read_bytes()
PY
echo CHECK_DID_NOT_CHANGE_PACKAGES
bash /kit/install.sh apply
rpm -qa | sort > /results/after-apply.txt
/usr/libexec/platform-python - <<'PY'
import json, glob
paths = sorted(glob.glob('/var/log/linuxoss-install/*/transaction.json'))
plan = json.load(open(paths[-1]))
assert plan['install_or_upgrade'], plan
assert any(p.startswith('linuxoss-openssl4-') for p in plan['install_or_upgrade']), plan
print('LOCAL_DEPENDENCY_SELECTED')
PY
curl --version
dnf --version
echo INSTALLER_CHECK_AND_APPLY_PASSED
