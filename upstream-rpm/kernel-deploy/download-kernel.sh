#!/usr/bin/env bash
# Download this exact kernel kit through the requested proxy, then check/apply.
set -Eeuo pipefail
umask 077
mode=${1:-check}
case "$mode" in check|apply) ;; *) echo 'Usage: sudo bash download-kernel.sh [check|apply]' >&2; exit 2;; esac
[[ $# -le 1 && $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
tag=linuxoss-kernel-20260925-2
archive="$tag.tar.gz"
expected=49adec3cfb3d50fee2121bf7c983878c9928eda25b615111345baef0d7b9b8a8
proxy=${LINUXOSS_PROXY:-http://192.168.32.104:9080}
base="https://github.com/emotionbug/slop/releases/download/$tag"
work=$(mktemp -d "$PWD/$tag.XXXXXXXX")
echo "Download and install directory: $work"
cd "$work"
wget -e use_proxy=yes -e "https_proxy=$proxy" -e "http_proxy=$proxy" \
  --https-only --timeout=60 --tries=3 -O "$archive.part" "$base/$archive"
printf '%s  %s\n' "$expected" "$archive.part" | sha256sum -c -
mv -- "$archive.part" "$archive"
tar --no-same-owner -xzf "$archive"
cd "$tag"
bash kernel.sh "$mode"
echo "Kernel kit retained at: $PWD"
echo 'No reboot performed. For an SSH-only trial: sudo bash kernel.sh boot-once-remote'
echo 'After reboot, reconnect and confirm within 20 minutes or the guard will request fallback reboot.'
