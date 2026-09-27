#!/usr/bin/env bash
# Offline Trivy scan with the exact kernel OpenVEX plus the independent source audit.
set -Eeuo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
trivy_bin=${1:?Usage: sudo bash scan-kernel-vex.sh TRIVY CACHE_DIR NEW_OUTPUT_DIR}
cache=${2:?}
output=${3:?}
[[ $EUID == 0 && -x $trivy_bin && -s $cache/db/trivy.db && ! -e $output ]] || exit 2
mkdir -p "$output"
"$trivy_bin" --config /dev/null --cache-dir "$cache" rootfs / \
  --pkg-types os --scanners vuln --skip-db-update --skip-java-db-update \
  --offline-scan --skip-check-update --skip-version-check --disable-telemetry \
  --skip-vex-repo-update --vex "$here/el8-168-kabi-final.openvex.json" \
  --show-suppressed --format json --output "$output/trivy-with-vex.json" \
  --timeout 60m --parallel 2 --no-progress
cp "$here/el8-168-final-cve-accounting-kabi-final.json" "$output/"
cp "$here/el8-168-kabi-final.openvex.json" "$output/"
uname -r > "$output/running-kernel.txt"
rpm -q kernel-linuxoss-el8-compat kernel-linuxoss-el8-compat-devel > "$output/kernel-rpms.txt"
echo 'TRIVY_AND_KERNEL_SOURCE_AUDIT_COMPLETED'
