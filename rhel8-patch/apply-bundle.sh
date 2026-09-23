#!/usr/bin/env bash
set -euo pipefail
proxy=direct
if [[ ${1:-} == --proxy ]]; then
  [[ $# -ge 2 ]] || { echo 'Missing proxy URL' >&2; exit 2; }
  proxy=$2
  shift 2
fi
mode=${1:-check}
[[ $# == 0 ]] || shift
[[ $# == 0 && ( $mode == check || $mode == apply ) ]] || {
  echo 'Usage: sudo bash apply-bundle.sh [--proxy URL|direct] [check|apply]' >&2
  exit 2
}
[[ $EUID == 0 ]] || { echo 'Run with sudo' >&2; exit 2; }
base=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
cd -- "$base"
sha256sum --check SHA256SUMS
selected=$(mktemp -d)
trap 'rm -rf -- "$selected"' EXIT
count=0
shopt -s nullglob
for file in "$base"/rpms/*.rpm; do
  package=$(rpm -qp --qf '%{NAME}.%{ARCH}' "$file")
  if rpm -q "$package" >/dev/null 2>&1; then
    ln -s -- "$file" "$selected/$(basename -- "$file")"
    printf 'Selected installed package: %s\n' "$package"
    count=$((count + 1))
  fi
done
if [[ $count == 0 ]]; then
  echo 'No installed packages match the RPM bundle.'
  exit 0
fi
bash "$base/patch-rhel8.sh" --proxy "$proxy" "rpm-$mode" "$selected"
