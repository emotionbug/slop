#!/usr/bin/env bash
# Build initramfs and arm a one-shot boot. This script never reboots the host.
set -Eeuo pipefail
umask 077

TARGET='4.18.0-553.168.1.linuxoss1.el8_10.x86_64'
IMAGE_SHA='47ced1f0d45b1b9a0381b39d3ff892be67f71fc29d2449424120a6c0f16c9100'
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
mode=${1:-check}
[[ $# -le 1 && ( $mode == check || $mode == apply ) ]] || {
  echo 'Usage: sudo bash prepare-ssh-boot.sh [check|apply]' >&2; exit 2;
}
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
. /etc/os-release
[[ $ID == rhel && $VERSION_ID == 8.* && $(uname -m) == x86_64 ]] || exit 2
for command in dracut grubby grub2-reboot grub2-editenv sha256sum systemctl modinfo; do
  command -v "$command" >/dev/null
done

kernel=/boot/vmlinuz-$TARGET
initramfs=/boot/initramfs-$TARGET.img
modules=/lib/modules/$TARGET/extra/linuxoss-reviewed
sha256sum -c <<<"$IMAGE_SHA  $kernel"
for name in gc-enforcement.ko dsa_filter_hook.ko dsa_filter.ko; do
  [[ -s $modules/$name && ! -L $modules/$name ]] || {
    echo "Missing reviewed module: $modules/$name" >&2; exit 2;
  }
done
[[ $(modinfo -k "$TARGET" -F name gc_enforcement) == gc_enforcement ]]
[[ $(modinfo -k "$TARGET" -F name dsa_filter_hook) == dsa_filter_hook ]]
[[ $(modinfo -k "$TARGET" -F name dsa_filter) == dsa_filter ]]

default_before=$(grubby --default-kernel)
printf 'Current default: %s\nTarget: %s\n' "$default_before" "$kernel"
if [[ $mode == check ]]; then
  echo CHECK_COMPLETED_NO_CHANGES
  exit 0
fi

state=/var/lib/linuxoss-kernel-compat
install -d -m 0700 "$state" /var/log/linuxoss-kernel-compat
if [[ ! -e $state/original-default-kernel ]]; then
  printf '%s\n' "$default_before" > "$state/original-default-kernel"
fi

dracut --force "$initramfs" "$TARGET"
[[ -s $initramfs ]]

args='panic=60 nmi_watchdog=1 softlockup_panic=1 hung_task_panic=1'
if grubby --info="$kernel" >/dev/null 2>&1; then
  existing_info=$(grubby --info="$kernel")
  grep -Fq "$initramfs" <<<"$existing_info" || {
    echo "Existing boot entry does not use $initramfs; refusing to rewrite it." >&2
    exit 2
  }
  grubby --update-kernel="$kernel" --args="$args"
else
  grubby --grub2 --add-kernel="$kernel" --initrd="$initramfs" \
    --title="Linux OSS EL8 compatibility $TARGET" --copy-default --args="$args"
fi
info=$(grubby --info="$kernel")
grep -Fq "$initramfs" <<<"$info"
entry=$(sed -n 's/^id="\(.*\)"$/\1/p' <<<"$info" | head -n 1)
[[ -n $entry ]] || { echo 'No BLS/GRUB entry id found.' >&2; exit 2; }

install -m 0755 "$here/linuxoss-boot-health.sh" /usr/local/sbin/linuxoss-boot-health
cat > /etc/systemd/system/linuxoss-boot-guard.service <<'UNIT'
[Unit]
Description=Rollback an unhealthy Linux OSS trial kernel
After=network-online.target sshd.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/linuxoss-boot-health
UNIT
cat > /etc/systemd/system/linuxoss-boot-guard.timer <<'UNIT'
[Unit]
Description=Validate the Linux OSS trial kernel after boot

[Timer]
OnBootSec=12min
AccuracySec=15s
Unit=linuxoss-boot-guard.service

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable linuxoss-boot-guard.timer >/dev/null
grub2-reboot "$entry"
[[ $(grubby --default-kernel) == "$default_before" ]]
grub2-editenv list > "$state/grubenv-after-arm.txt"
printf '%s\n' "$entry" > "$state/trial-entry"
echo ONE_SHOT_BOOT_ARMED_NO_REBOOT
echo "Next boot: $TARGET"
echo "Persistent default remains: $default_before"
