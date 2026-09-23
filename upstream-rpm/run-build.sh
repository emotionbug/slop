#!/usr/bin/env bash
# Snapshot the entry script so edits to the bind-mounted recipe cannot change
# the shell input halfway through a long compiler/kernel build.
set -euo pipefail
[[ $# -ge 2 ]] || { echo 'Usage: run-build.sh build-rpm.sh|build-kernel.sh ARGUMENT' >&2; exit 2; }
case "$1" in
  build-rpm.sh|build-kernel.sh) entry=$1 ;;
  *) echo 'Unsupported build entry point' >&2; exit 2 ;;
esac
shift
[[ $(id -u) -ne 0 ]] || exit 2
snapshot=$(mktemp /tmp/linuxoss-build-entry.XXXXXX)
cp -- "/recipe/$entry" "$snapshot"
chmod 0500 "$snapshot"
exec bash "$snapshot" "$@"
