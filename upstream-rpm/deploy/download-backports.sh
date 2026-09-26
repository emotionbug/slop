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
  --timeout=60 --tries=3 -O linuxoss-backports-20260926-1.tar.gz \
  https://github.com/emotionbug/slop/releases/download/linuxoss-backports-20260926-1/linuxoss-backports-20260926-1.tar.gz
printf '%s  %s\n' 'a29d19bb8556a5b982b8312ce0cbe65a2b4bc2448d61d4e77cfa9e1a293bb7b9' 'linuxoss-backports-20260926-1.tar.gz' | sha256sum -c -
tar --no-same-owner -xzf linuxoss-backports-20260926-1.tar.gz
kit="$work/linuxoss-backports-20260926-1"
echo "Kit retained at: $kit"
bash "$kit/install.sh" "$mode" "$@"
echo "Kit retained at: $kit"
