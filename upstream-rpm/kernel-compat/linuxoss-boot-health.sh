#!/usr/bin/env bash
set -Eeuo pipefail

TARGET=$(/usr/libexec/platform-python -c 'import json; print(json.load(open("/usr/share/linuxoss-kernel-compat/server-profile-module-manifest-final.json"))["release"])')
STATE=/var/lib/linuxoss-kernel-compat
ORIGINAL="$STATE/original-default-kernel"
LOG=/var/log/linuxoss-kernel-compat/boot-guard.log
MARKER=/run/linuxoss-kernel-compat/agent-health.ok

mkdir -p "$(dirname "$LOG")" "$STATE" "$(dirname "$MARKER")"
exec >>"$LOG" 2>&1
echo "$(date -u +%FT%TZ) boot guard: running=$(uname -r)"

[[ $(uname -r) == "$TARGET" ]] || exit 0
[[ -e "$STATE/confirmed-$TARGET" ]] && exit 0

failed=()
systemctl is-active --quiet sshd.service || failed+=(sshd)
systemctl is-active --quiet network-online.target || failed+=(network-online)
ip route show default | grep -q . || failed+=(default-route)

# Select the root-owned local running-module profile when it was staged;
# otherwise retain the signed-overlay verification path.
if [[ -s $STATE/local-module-profile.json ]]; then
  /usr/libexec/platform-python /usr/local/libexec/linuxoss-kernel-compat/stage-reviewed-modules.py \
    --local-profile-check >/dev/null 2>&1 || failed+=(local-module-profile)
else
  /usr/libexec/platform-python /usr/local/libexec/linuxoss-kernel-compat/stage-reviewed-modules.py \
    check >/dev/null 2>&1 || failed+=(signed-agent-profile)
fi

services=/etc/linuxoss-kernel-compat/health-services
if [[ -r $services ]]; then
  [[ $(stat -c '%u:%a' "$services") == 0:600 ]] || failed+=(health-service-config)
  while IFS= read -r service; do
    [[ -z $service || $service == \#* ]] && continue
    [[ $service =~ ^[A-Za-z0-9_.@:-]+$ ]] || { failed+=(health-service-config); continue; }
    systemctl is-active --quiet "$service" || failed+=(configured-agent-service)
  done < "$services"
fi

if ((${#failed[@]} == 0)); then
  printf 'healthy\n' > "$MARKER"
  touch "$STATE/healthy-$TARGET"
  grubby --set-default "/boot/vmlinuz-$TARGET"
  touch "$STATE/confirmed-$TARGET"
  systemctl disable linuxoss-boot-guard.timer >/dev/null 2>&1 || true
  echo "$(date -u +%FT%TZ) boot guard: SSH, network, agent modules and configured services passed; default committed"
  exit 0
fi

rm -f "$MARKER"
echo "$(date -u +%FT%TZ) boot guard failed: ${failed[*]}"
if [[ -s "$ORIGINAL" ]]; then
  grubby --set-default "$(<"$ORIGINAL")"
fi
grub2-editenv - unset next_entry || true
sync
systemctl reboot --message='linuxoss trial kernel health failure; reverting to saved kernel'
