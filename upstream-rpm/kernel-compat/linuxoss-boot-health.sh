#!/usr/bin/env bash
set -Eeuo pipefail

TARGET='4.18.0-553.168.1.linuxoss1.el8_10.x86_64'
STATE=/var/lib/linuxoss-kernel-compat
ORIGINAL="$STATE/original-default-kernel"
LOG=/var/log/linuxoss-kernel-compat/boot-guard.log

mkdir -p "$(dirname "$LOG")" "$STATE"
exec >>"$LOG" 2>&1
echo "$(date -u +%FT%TZ) boot guard: running=$(uname -r)"

[[ $(uname -r) == "$TARGET" ]] || exit 0
[[ -e "$STATE/confirmed-$TARGET" ]] && exit 0

failed=()
systemctl is-active --quiet sshd.service || failed+=(sshd)
ip route show default | grep -q . || failed+=(default-route)

check_module() {
  local module=$1 field=$2 expected=$3 value=''
  [[ -r /sys/module/$module/$field ]] && value=$(<"/sys/module/$module/$field")
  [[ $value == "$expected" ]] || failed+=("$module-$field")
}
check_module gc_enforcement srcversion 1E3CF09EA0054B840FB024B
check_module dsa_filter_hook srcversion 533BB7E5866E52F63B9ACCB
check_module dsa_filter version '12.6.0.8491 (HUA)'

if ((${#failed[@]} == 0)); then
  touch "$STATE/healthy-$TARGET"
  systemctl disable linuxoss-boot-guard.timer >/dev/null 2>&1 || true
  echo "$(date -u +%FT%TZ) boot guard: SSH, route and exact Trend/Guardicore modules passed"
  exit 0
fi

echo "$(date -u +%FT%TZ) boot guard failed: ${failed[*]}"
if [[ -s "$ORIGINAL" ]]; then
  original=$(<"$ORIGINAL")
  grubby --set-default "$original"
fi
sync
systemctl reboot --message="linuxoss trial kernel health failure: ${failed[*]}"
