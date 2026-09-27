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
  --timeout=60 --tries=3 -O linuxoss-kernel-compat-20260927-5.tar.gz \
  https://github.com/emotionbug/slop/releases/download/linuxoss-kernel-compat-20260927-5/linuxoss-kernel-compat-20260927-5.tar.gz
printf '%s  %s\n' '91052b2ec99367cc06a06ebc1898162cadf6044a7b73ce76c6ece868d242b1ed' 'linuxoss-kernel-compat-20260927-5.tar.gz' | sha256sum -c -
tar --no-same-owner -xzf linuxoss-kernel-compat-20260927-5.tar.gz
kit="$work/linuxoss-kernel-compat-20260927-5"
echo "Kit retained at: $kit"
if [[ $mode == apply ]]; then
  bash "$kit/install-kernel-compat.sh" "$@"
else
  bash "$kit/stage-kernel.sh" check "$@"
fi
echo "Kit retained at: $kit"
