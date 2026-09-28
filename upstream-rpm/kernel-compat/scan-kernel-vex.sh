#!/usr/bin/env bash
# Offline raw, filtered, and auditable Trivy scans for the exact custom kernel RPM.
set -Eeuo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
trivy_bin=${1:?Usage: sudo bash scan-kernel-vex.sh TRIVY CACHE_DIR NEW_OUTPUT_DIR [final|audit|both]}
cache=${2:?}
output=${3:?}
mode=${4:-both}
[[ $mode == final || $mode == audit || $mode == both ]] || {
  echo "ERROR: mode must be final, audit, or both" >&2
  exit 2
}
[[ $EUID == 0 && -x $trivy_bin && -s $cache/db/trivy.db && ! -e $output \
   && -s $here/openvex.json && -s $here/build-exact-product-openvex.py ]] || exit 2
mkdir -p "$output"

common=(--config /dev/null --cache-dir "$cache" rootfs / \
  --pkg-types os --scanners vuln --skip-db-update --skip-java-db-update \
  --offline-scan --skip-check-update --skip-version-check --disable-telemetry \
  --skip-vex-repo-update --timeout 60m --parallel 2 --no-progress)

# The raw report is the authority for installed package PURLs.  It is retained
# unchanged and is never described as clean.
"$trivy_bin" "${common[@]}" --format json --output "$output/trivy-raw.json"
python3 "$here/build-exact-product-openvex.py" \
  --trivy-report "$output/trivy-raw.json" \
  --semantic-openvex "$here/openvex.json" \
  --output "$output/openvex.exact.json" \
  > "$output/openvex-binding-summary.json"

# final: only findings that remain after exact-product VEX are present.
if [[ $mode == final || $mode == both ]]; then
  "$trivy_bin" "${common[@]}" --vex "$output/openvex.exact.json" \
    --format json --output "$output/trivy-final.json"
fi
# audit: suppressed findings are retained as ExperimentalModifiedFindings.
if [[ $mode == audit || $mode == both ]]; then
  "$trivy_bin" "${common[@]}" --vex "$output/openvex.exact.json" \
    --show-suppressed --format json --output "$output/trivy-audit.json"
fi
cp "$here/openvex.json" "$output/openvex.semantic.json"
uname -r > "$output/running-kernel.txt"
rpm -q kernel-linuxoss-el8-compat kernel-linuxoss-el8-compat-devel \
  > "$output/kernel-rpms.txt" 2>&1 || true
echo 'TRIVY_RAW_EXACT_VEX_AND_AUDIT_COMPLETED'
