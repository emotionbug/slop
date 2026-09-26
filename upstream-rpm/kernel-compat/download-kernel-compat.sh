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
  --timeout=60 --tries=3 -O linuxoss-kernel-compat-20260926-1.tar.gz \
  https://github.com/emotionbug/slop/releases/download/linuxoss-backports-20260926-1/linuxoss-kernel-compat-20260926-1.tar.gz
printf '%s  %s\n' '3063ad6eaf628f23910563db2b5281212864645fdb29102a4abc9e9c4e170425' 'linuxoss-kernel-compat-20260926-1.tar.gz' | sha256sum -c -
tar --no-same-owner -xzf linuxoss-kernel-compat-20260926-1.tar.gz
kit="$work/linuxoss-kernel-compat-20260926-1"
echo "Kit retained at: $kit"
bash "$kit/stage-kernel.sh" "$mode" "$@"
echo "Kit retained at: $kit"
