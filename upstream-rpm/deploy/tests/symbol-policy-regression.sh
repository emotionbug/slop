#!/usr/bin/env bash
set -euo pipefail
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
trap 'cp -a /var/log/linuxoss-install/. /results/ 2>/dev/null || true' EXIT
rpm -q cups-libs | tee /results/old-cups.txt
[[ -f /usr/lib64/libcupscgi.so.1 ]]
install -m 0755 /results/removed-cgi-consumer.so /usr/local/lib/linuxoss-test-cgi-consumer.so
ln -s missing-fixture-target /usr/local/lib/linuxoss-test-dangling
mkdir -p /usr/src/linuxoss-policy-fixture /usr/lib/modules/linuxoss-policy-fixture
ln -s /usr/src/linuxoss-policy-fixture /usr/lib/modules/linuxoss-policy-fixture/build
rpm -qa | sort > /results/before.txt
if bash /kit/install.sh check > /results/expected-block.log 2>&1; then
    echo 'External CGI import was incorrectly allowed' >&2; exit 2
fi
grep -q 'Symbol imports or incomplete audit found' /results/expected-block.log
rpm -qa | sort > /results/after-block.txt
cmp /results/before.txt /results/after-block.txt
/usr/libexec/platform-python - <<'PY'
import glob, json
policy = json.load(open(sorted(glob.glob('/var/log/linuxoss-install/run-*/symbol-audit-policy.json'))[-1]))
assert any('cgiGetSize' in m['symbols'] for m in policy['blocking_matches']), policy
assert any(a['evidence']['reason'] == 'consumer_file_removed_by_same_transaction'
           for a in policy['accepted_matches']), policy
assert policy['preexisting_dangling_links'], policy
assert not policy['uncovered_directory_links'], policy
print('SURVIVING_CGI_IMPORT_BLOCKED_WITHOUT_RPM_CHANGES')
PY
rm -- /usr/local/lib/linuxoss-test-cgi-consumer.so
bash /kit/install.sh apply > /results/apply.log 2>&1
rpm -qa | sort > /results/after-apply.txt
[[ ! -e /usr/lib64/libcupscgi.so.1 ]]
[[ -f /usr/lib64/libcups.so.2 ]]
[[ -L /usr/local/lib/linuxoss-test-dangling ]]
dnf --noplugins --disablerepo='*' check
rpm -q cups-libs linuxoss-test-legacy-consumer
rpm -q --whatprovides /bin/sed /bin/awk /bin/tar
curl --version
/usr/libexec/platform-python - <<'PY'
import ctypes, glob, json
paths = sorted(glob.glob('/var/log/linuxoss-install/run-*/symbol-audit-policy.json'))
policy = json.load(open(paths[-1]))
assert policy['allow_transaction'], policy
assert not policy['blocking_matches'], policy
lib = ctypes.CDLL('libcups.so.2')
lib.cupsGetDefault.restype = ctypes.c_void_p
# Load/link only: do not query a print server or change print configuration.
plan = json.load(open(paths[-1].replace('symbol-audit-policy.json','transaction.json')))
print('UPGRADES', len(plan['requested_upgrades']), 'INCOMING', len(plan['install_or_upgrade']))
print('CUPS_UPGRADE_AND_LOCAL_DNF_CHECK_PASSED')
PY
