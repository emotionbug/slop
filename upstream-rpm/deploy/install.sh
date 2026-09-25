#!/usr/bin/env bash
# Offline installer for the exact reference-tested manifest.
set -Eeuo pipefail
umask 077
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
mode=${1:-check}
[[ $# == 0 ]] || shift
case "$mode" in check|apply) ;; *) echo 'Usage: sudo bash install.sh [check|apply] [additional application directories...]' >&2; exit 2;; esac
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
. /etc/os-release
[[ $ID == rhel && $VERSION_ID == 8.* && $(uname -m) == x86_64 ]] || {
    echo 'Requires RHEL 8 x86_64.' >&2; exit 2;
}
[[ -x /usr/libexec/platform-python ]] || exit 2
for command in rpm dnf tar sha256sum readelf flock; do command -v "$command" >/dev/null || exit 2; done
exec 9>/run/linuxoss-install.lock
flock -n 9 || { echo 'Another linuxoss installation is running.' >&2; exit 2; }
cd -- "$here"
sha256sum --quiet -c SHA256SUMS
mkdir -p /var/log/linuxoss-install
report=$(mktemp -d /var/log/linuxoss-install/run-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX)
exec > >(tee -a "$report/install.log") 2>&1
echo "Report: $report"
echo STARTED > "$report/status.txt"
trap 'echo FAILED_CHECK_STATUS_AND_DNF_HISTORY > "$report/status.txt"; echo "Stopped. See $report/install.log" >&2' ERR
rpm -qa --qf '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n' | sort > "$report/rpms-before.tsv"
uname -r > "$report/running-kernel.txt"
/usr/libexec/platform-python "$here/install-rpms.py" "$mode" "$here" "$report" "$@"
if [[ $mode == apply ]]; then
    dnf --noplugins --disablerepo='*' check
    rpm -qa --qf '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n' | sort > "$report/rpms-after.tsv"
    echo APPLY_COMPLETED > "$report/status.txt"
    echo 'Apply completed. Restart Java/Tomcat in your maintenance window, then run scan.sh.'
else
    echo CHECK_COMPLETED_NO_INSTALL > "$report/status.txt"
    echo 'Check completed; no RPMs were installed. Apply: sudo bash install.sh apply [application directories...]'
fi
echo "Report: $report"
