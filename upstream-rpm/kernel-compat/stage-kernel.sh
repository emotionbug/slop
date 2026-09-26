#!/usr/bin/env bash
# Stage the exact tested parallel kernel RPMs. No boot configuration is changed.
set -Eeuo pipefail
umask 077
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
mode=${1:-check}
[[ $# -le 1 && ( $mode == check || $mode == apply ) ]] || {
  echo 'Usage: sudo bash stage-kernel.sh [check|apply]' >&2; exit 2;
}
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
. /etc/os-release
[[ $ID == rhel && $VERSION_ID == 8.* && $(uname -m) == x86_64 ]] || {
  echo 'Requires RHEL 8 x86_64.' >&2; exit 2;
}
for command in rpm sha256sum grubby flock; do command -v "$command" >/dev/null; done
exec 9>/run/linuxoss-install.lock
flock -n 9 || { echo 'Another linuxoss installation is running.' >&2; exit 2; }
cd -- "$here"
sha256sum --quiet -c SHA256SUMS
mkdir -p /var/log/linuxoss-kernel-compat
report=$(mktemp -d /var/log/linuxoss-kernel-compat/stage-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX)
exec > >(tee -a "$report/stage.log") 2>&1
echo "Report: $report"
uname -r > "$report/running-kernel.txt"
grubby --default-kernel > "$report/default-before.txt"
rpm -qa --qf '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n' | sort > "$report/rpms-before.tsv"
shopt -s nullglob
files=("$here"/rpms/*.rpm)
[[ ${#files[@]} == 2 ]] || { echo 'Expected exactly two pinned kernel RPMs.' >&2; exit 2; }
pending=()
for file in "${files[@]}"; do
  name=$(rpm -qp --qf '%{NAME}' "$file")
  [[ $name == kernel-linuxoss-el8-compat || $name == kernel-linuxoss-el8-compat-devel ]] || exit 2
  nevra=$(rpm -qp --qf '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}' "$file")
  if rpm -q "$nevra" >/dev/null 2>&1; then
    rpm -V "$nevra"
    echo "Already staged and verified: $nevra"
  else
    pending+=("$file")
  fi
done
if [[ ${#pending[@]} -gt 0 ]]; then
  rpm --test -ivh "${pending[@]}"
  if [[ $mode == apply ]]; then
    rpm -ivh "${pending[@]}"
    for file in "${pending[@]}"; do
      nevra=$(rpm -qp --qf '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}' "$file")
      rpm -V "$nevra"
    done
  fi
fi
grubby --default-kernel > "$report/default-after.txt"
cmp "$report/default-before.txt" "$report/default-after.txt"
rpm -qa --qf '%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n' | sort > "$report/rpms-after.tsv"
if [[ $mode == check ]]; then
  cmp "$report/rpms-before.tsv" "$report/rpms-after.tsv"
  echo CHECK_COMPLETED_NO_INSTALL
else
  echo STAGED_ONLY_NO_BOOT_CHANGE
  echo 'No initramfs, GRUB entry, default change or reboot was performed.'
  echo 'The running kernel is unchanged; its CVEs are not remediated by staging.'
fi
