#!/usr/bin/env bash
# Versioned kernel install, one-time boot, and explicit confirmation on RHEL 8.
set -Eeuo pipefail
umask 077
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
mode=${1:-status}
case "$mode" in check|apply|boot-once|boot-once-remote|confirm|fallback|status) ;; *) echo 'Usage: sudo bash kernel.sh [check|apply|boot-once|boot-once-remote|confirm|fallback|status]' >&2; exit 2;; esac
[[ $# -le 1 ]] || exit 2
. /etc/os-release
[[ $ID == rhel && $VERSION_ID == 8.* && $(uname -m) == x86_64 ]] || exit 2
for command in flock sha256sum rpm rpm2cpio cpio grubby grub2-editenv grub2-reboot dracut lsinitrd depmod modinfo findmnt; do
    command -v "$command" >/dev/null || { echo "Required command missing: $command" >&2; exit 2; }
done
exec 9>/run/linuxoss-kernel.lock
flock -n 9 || { echo 'Another kernel operation is running.' >&2; exit 2; }
(cd "$here"; sha256sum --quiet -c SHA256SUMS)
mkdir -p /var/log/linuxoss-kernel
report=$(mktemp -d /var/log/linuxoss-kernel/run-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX)
exec > >(tee -a "$report/kernel.log") 2>&1
echo "Report: $report"
echo STARTED > "$report/status.txt"
trap 'echo FAILED_REVIEW_KERNEL_LOG > "$report/status.txt"' ERR
/usr/libexec/platform-python "$here/kernel.py" "$mode" "$here" "$report"
echo COMPLETED > "$report/status.txt"
