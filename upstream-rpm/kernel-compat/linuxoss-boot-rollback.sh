#!/usr/bin/env bash
set -Eeuo pipefail
STATE=/var/lib/linuxoss-kernel-compat
[[ $EUID == 0 && -s $STATE/original-default-kernel ]] || exit 2
grubby --set-default "$(<"$STATE/original-default-kernel")"
grub2-editenv - unset next_entry || true
sync
systemctl reboot --message='linuxoss trial kernel health check failed; restoring prior default'
