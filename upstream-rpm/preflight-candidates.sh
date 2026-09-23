#!/usr/bin/env bash
# Collect one read-only review report; never install/remove/restart anything.
set -uo pipefail
umask 077
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
report=$(mktemp -d "${PWD}/rpm-preflight.XXXXXX") || exit 2
python=${PYTHON:-/usr/libexec/platform-python}
[[ -x $python ]] || python=$(command -v python3) || exit 2
[[ -d $here/rpms && -f $here/expected-export-removals.json ]] || {
  echo 'Run the copy included in an extracted candidate bundle.' >&2; exit 2;
}
(cd "$here" && sha256sum -c SHA256SUMS) > "$report/checksums.txt" 2>&1 || {
  echo "Checksum failure: $report/checksums.txt" >&2; exit 2;
}
"$python" "$here/check-removed-symbol-users.py" \
  --symbols-file "$here/expected-export-removals.json" "$@" > "$report/symbol-audit.json"
symbol_status=$?
dnf --disableplugin=subscription-manager --disablerepo='*' \
  --setopt=localpkg_gpgcheck=False --setopt=install_weak_deps=False \
  --assumeno install "$here"/rpms/*.rpm > "$report/dnf-preview.txt" 2>&1
dnf_status=$?
printf 'symbol_audit_exit=%s\ndnf_preview_exit=%s\nPackages were not installed. DNF --assumeno can return 1 after declining the transaction.\n' \
  "$symbol_status" "$dnf_status" > "$report/status.txt"
echo "Reports: $report"
echo 'Review both symbol-audit.json and dnf-preview.txt together.'
echo 'No matching imports does not cover dlsym, plugins, omitted application paths or running deleted binaries.'
exit 0
