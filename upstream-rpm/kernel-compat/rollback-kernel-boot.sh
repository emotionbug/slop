#!/usr/bin/env bash
set -Eeuo pipefail
STATE=/var/lib/linuxoss-kernel-compat
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
[[ -s $STATE/original-default-kernel ]] || { echo 'Original default is not recorded.' >&2; exit 2; }
original=$(<"$STATE/original-default-kernel")
grubby --set-default "$original"
grub2-editenv - unset next_entry || true
systemctl disable --now linuxoss-boot-guard.timer >/dev/null 2>&1 || true
echo "RESTORED_DEFAULT_KERNEL=$original"
echo 'No reboot was performed.'
