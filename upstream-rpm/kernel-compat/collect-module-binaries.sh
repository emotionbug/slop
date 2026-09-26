#!/usr/bin/env bash
# Collect only module payloads for local ABI analysis, never keys/configuration.
set -Eeuo pipefail
umask 077
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
[[ $# -le 1 ]] || { echo 'Usage: sudo bash collect-module-binaries.sh [new-output-directory]' >&2; exit 2; }
output=${1:-"$PWD/security-module-binaries-$(date -u +%Y%m%dT%H%M%SZ)-$$"}
[[ ! -e $output ]] || { echo 'Output already exists.' >&2; exit 2; }
mkdir -m 700 -- "$output"
output=$(cd -- "$output" && pwd -P)
uname -r > "$output/kernel-release.txt"
mkdir "$output/modules"
for name in gc_enforcement dsa_filter dsa_filter_hook; do
  modinfo "$name" > "$output/$name-modinfo.txt" 2>&1 || :
  if [[ -d /sys/module/$name ]]; then echo loaded; else echo not-loaded; fi > "$output/$name-state.txt"
  # modinfo follows the disk alias, which can differ from the loaded module.
  for field in version srcversion taint; do
    [[ ! -f /sys/module/$name/$field ]] || cat "/sys/module/$name/$field" > "$output/$name-loaded-$field.txt"
  done
done
# Restrict traversal to known kernel/agent trees; copy module binaries only.
roots=()
for path in "/lib/modules/$(uname -r)" /opt/ds_agent /opt/guardicore /usr/lib/guardicore; do
  [[ ! -d $path ]] || roots+=("$path")
done
count=0
if [[ ${#roots[@]} -gt 0 ]]; then
  while IFS= read -r -d '' path; do
    resolved=$(readlink -f -- "$path")
    [[ -f $resolved ]] || continue
    digest=$(sha256sum -- "$resolved")
    digest=${digest%% *}
    base=$(basename -- "$resolved")
    destination="$output/modules/$digest-$base"
    [[ -e $destination ]] || cp -- "$resolved" "$destination"
    printf '%s\t%s\n' "$digest" "$path" >> "$output/origins.tsv"
    count=$((count + 1))
  done < <(find "${roots[@]}" \( -type f -o -type l \) \
    \( -name 'gc-enforcement.ko*' -o -name 'gc_enforcement.ko*' \
       -o -name 'dsa_filter.ko*' -o -name 'dsa_filter_hook.ko*' \) -print0)
fi
[[ $count -gt 0 ]] || { echo "No module payload found. Metadata retained at: $output" >&2; exit 3; }
(cd -- "$output" && find modules -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
tar -czf "$output.tar.gz" -C "$(dirname -- "$output")" "$(basename -- "$output")"
echo "Private analysis archive: $output.tar.gz"
echo 'Contains agent binaries. No upload was performed; do not publish it to a public repository.'
