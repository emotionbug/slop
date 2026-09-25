#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
if [[ $# == 0 ]]; then
    trivy=''
    cache=''
    for candidate in /root/trivy/trivy-proxy-work/bin/trivy /root/trivy/trivy /root/trivy/trivy-proxy-work/trivy /usr/local/bin/trivy; do
        if [[ -x $candidate ]]; then trivy=$candidate; break; fi
    done
    for candidate in /root/trivy/trivy-proxy-work/cache /root/trivy/cache /root/.cache/trivy; do
        if [[ -s $candidate/db/trivy.db && -s $candidate/db/metadata.json ]]; then cache=$candidate; break; fi
    done
    [[ -n $trivy && -n $cache ]] || {
        echo 'Trivy or DB not found. Usage: sudo bash scan.sh /actual/path/trivy /actual/path/cache [new-report-directory]' >&2; exit 2;
    }
    set -- "$trivy" "$cache"
fi
[[ $# == 2 || $# == 3 ]] || {
    echo 'Usage: sudo bash scan.sh [/path/to/trivy /path/to/cache [new-report-directory]]' >&2; exit 2;
}
output=${3:-/var/log/linuxoss-trivy/scan-$(date -u +%Y%m%dT%H%M%SZ)-$$}
echo "Trivy: $1"
echo "Cache: $2"
bash "$here/native-trivy/scan-native.sh" --trivy "$1" --cache-dir "$2" --output-dir "$output"
echo "Check vulnerabilities: $output/reports/actionable.csv"
echo "Available vendor fixes: $output/reports/fix-available.csv"
echo "Custom RPM review: $output/reports/native-review.csv"
