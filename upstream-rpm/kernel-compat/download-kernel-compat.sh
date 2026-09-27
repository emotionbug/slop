#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
mode=${1:-check}
[[ $# == 0 ]] || shift
[[ $mode == check || $mode == apply ]] || { echo 'Use check or apply.' >&2; exit 2; }
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
proxy=${LINUXOSS_PROXY:-http://192.168.32.104:9080}
work=$(mktemp -d "${PWD}/linuxoss-download-XXXXXXXX")
echo "Download directory: $work"
cd -- "$work"
wget -e use_proxy=yes -e "https_proxy=$proxy" -e "http_proxy=$proxy" \
  --timeout=60 --tries=3 -O linuxoss-kernel-compat-20260927-3.tar.gz \
  https://github.com/emotionbug/slop/releases/download/linuxoss-kernel-compat-20260927-3/linuxoss-kernel-compat-20260927-3.tar.gz
printf '%s  %s\n' 'fd8b50dfd783a8a0152cd846c8376bd46640f60b2d26fa326968edfe6b29c5aa' 'linuxoss-kernel-compat-20260927-3.tar.gz' | sha256sum -c -
tar --no-same-owner -xzf linuxoss-kernel-compat-20260927-3.tar.gz
kit="$work/linuxoss-kernel-compat-20260927-3"
echo "Kit retained at: $kit"
if [[ $mode == apply ]]; then
  bash "$kit/install-kernel-compat.sh" "$@"
else
  bash "$kit/stage-kernel.sh" check "$@"
fi
echo "Kit retained at: $kit"
