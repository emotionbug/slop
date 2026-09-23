#!/usr/bin/env bash
set -euo pipefail
proxy=''
reset_proxy=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --proxy)
      [[ $# -ge 2 && -n $2 ]] || { echo 'Missing host:port' >&2; exit 2; }
      proxy=${2#http://}
      shift 2 ;;
    --reset-rhsm-proxy) reset_proxy=true; shift ;;
    -h|--help)
      echo 'Usage: sudo bash rollback-registration.sh [--proxy HOST:PORT] [--reset-rhsm-proxy]'
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ $EUID == 0 ]] || { echo 'Run with sudo' >&2; exit 2; }
command -v subscription-manager >/dev/null
umask 077
backup_dir="/var/lib/rhel8-patch/rollback-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p -- "$backup_dir"
cp -p -- /etc/rhsm/rhsm.conf "$backup_dir/rhsm.conf.before"
args=()
[[ -z $proxy ]] || args+=(--proxy "$proxy")
# Stop on a server-side failure: do not abandon a still-registered consumer.
subscription-manager unregister "${args[@]}"
subscription-manager clean
if $reset_proxy; then
  subscription-manager config --remove=server.proxy_hostname
  subscription-manager config --remove=server.proxy_port
fi
if [[ -e /etc/pki/consumer/cert.pem ]]; then
  echo 'Consumer certificate still exists; inspect subscription-manager output.' >&2
  exit 1
fi
printf 'Registration removed. RHSM configuration backup: %s\n' "$backup_dir"
