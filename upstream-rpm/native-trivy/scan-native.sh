#!/usr/bin/env bash
# RHEL 8: one Trivy rootfs scan with the local evidence module and one CSV export.
set -Eeuo pipefail
umask 077
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
TRIVY_BIN=''
CACHE_DIR=''
OUT_DIR=''
FAIL_ON_GAP=()
while (($#)); do
    case "$1" in
        --trivy) TRIVY_BIN=${2:?executable path required}; shift 2 ;;
        --cache-dir) CACHE_DIR=${2:?Trivy cache path required}; shift 2 ;;
        --output-dir) OUT_DIR=${2:?new output directory required}; shift 2 ;;
        --fail-on-gap) FAIL_ON_GAP=(--fail-on-gap); shift ;;
        *) echo 'Usage: sudo bash scan-native.sh --trivy BIN --cache-dir DIR --output-dir NEW_DIR [--fail-on-gap]' >&2; exit 2 ;;
    esac
done
[[ $EUID == 0 && -x "$TRIVY_BIN" && -n "$CACHE_DIR" && -n "$OUT_DIR" ]] || exit 2
[[ ! -e "$OUT_DIR" ]] || { echo 'Output directory already exists' >&2; exit 2; }
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || exit 2
. /etc/os-release
[[ $ID == rhel && $VERSION_ID == 8* ]] || exit 2
for variable in ${!TRIVY_@}; do [[ $variable == TRIVY_BIN ]] || unset "$variable"; done
TRIVY_BIN=$(readlink -f -- "$TRIVY_BIN")
CACHE_DIR=$(readlink -f -- "$CACHE_DIR")
[[ -s "$CACHE_DIR/db/trivy.db" && -s "$CACHE_DIR/db/metadata.json" ]] || exit 2
[[ -s "$DIR/modules/linuxoss-artifact-evidence.wasm" && -s "$DIR/SHA256SUMS" ]] || exit 2
(cd "$DIR"; sha256sum --quiet -c SHA256SUMS)
export TRIVY_DISABLE_TELEMETRY=true TRIVY_SKIP_VERSION_CHECK=true
[[ $("$TRIVY_BIN" --config /dev/null --version | head -n 1) == 'Version: 0.74.0' ]] || { echo 'Requires Trivy 0.74.0' >&2; exit 2; }
mkdir -p -- "$OUT_DIR"
OUT_DIR=$(cd -- "$OUT_DIR" && pwd -P)
mkdir -p /run/linuxoss-trivy
INPUT_DIR=$(mktemp -d /run/linuxoss-trivy/scan.XXXXXXXX)
cleanup() {
    rm -f -- "$INPUT_DIR/linuxoss-installed-evidence.json"
    rmdir -- "$INPUT_DIR"
}
trap cleanup EXIT
echo RUNNING > "$OUT_DIR/status.txt"
trap 'echo FAILED > "$OUT_DIR/status.txt"' ERR
PY=/usr/libexec/platform-python
"$PY" "$DIR/collect-installed.py" --catalog "$DIR/catalog.json" \
    --output "$INPUT_DIR/linuxoss-installed-evidence.json"
cp "$INPUT_DIR/linuxoss-installed-evidence.json" "$OUT_DIR/installed-evidence.json"
cp "$CACHE_DIR/db/metadata.json" "$OUT_DIR/db-metadata.json"
mkdir "$OUT_DIR/home"
env HOME="$OUT_DIR/home" XDG_CONFIG_HOME="$OUT_DIR/home" \
    "$TRIVY_BIN" --config /dev/null --cache-dir "$CACHE_DIR" rootfs / \
    --module-dir "$DIR/modules" --enable-modules linuxoss-artifact-evidence \
    --pkg-types os --scanners vuln --skip-db-update --skip-java-db-update --offline-scan \
    --skip-check-update --skip-version-check --disable-telemetry --skip-vex-repo-update \
    --cache-backend memory --ignorefile /dev/null --list-all-pkgs --exit-code 0 \
    --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL --timeout 60m --parallel 2 --no-progress \
    --skip-dirs "$OUT_DIR" --skip-dirs "$CACHE_DIR" --skip-dirs "$DIR" \
    --skip-dirs /proc --skip-dirs /sys --skip-dirs /dev \
    --format json --output "$OUT_DIR/integrated.json" > "$OUT_DIR/scan.stdout.log" 2> "$OUT_DIR/scan.log"
rc=0
"$PY" "$DIR/report.py" "$OUT_DIR/integrated.json" --snapshot "$OUT_DIR/installed-evidence.json" \
    --output-dir "$OUT_DIR/reports" "${FAIL_ON_GAP[@]}" > "$OUT_DIR/summary.txt" || rc=$?
if ((rc != 0 && rc != 3)); then echo FAILED > "$OUT_DIR/status.txt"; exit "$rc"; fi
echo SCAN_COMPLETED_COVERAGE_INCOMPLETE > "$OUT_DIR/status.txt"
cat "$OUT_DIR/summary.txt"
echo "Integrated CSV: $OUT_DIR/reports/integrated.csv"
exit "$rc"
