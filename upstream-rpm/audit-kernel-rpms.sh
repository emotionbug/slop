#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 && -d $1 ]] || exit 2
mkdir -p /output
for rpmfile in "$1"/*.rpm; do
  rpm -qp --qf '%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\n' "$rpmfile"
  rpmkeys --checksig "$rpmfile"
  rpm -qpl "$rpmfile" > "/output/$(basename "$rpmfile").files.txt"
  rpm -qp --requires "$rpmfile" > "/output/$(basename "$rpmfile").requires.txt"
  rpm -qp --provides "$rpmfile" > "/output/$(basename "$rpmfile").provides.txt"
  rpm -qp --scripts "$rpmfile" > "/output/$(basename "$rpmfile").scripts.txt"
  if rpm -qpl "$rpmfile" | grep -E '(^|/)(signing_key\.pem|.*\.key|id_rsa|id_ed25519)$'; then
    echo 'Potential private key payload; review required' >&2; exit 1
  fi
done
workspace=$(mktemp -d /tmp/kernel-source-audit.XXXXXX)
cd "$workspace"
rpm2cpio "$1"/kernel-*.src.rpm | cpio -idm --quiet --no-absolute-filenames
tar -tzf linux.tar.gz > /output/kernel-source-file-list.txt
if grep -E '(^|/)certs/signing_key\.pem$' /output/kernel-source-file-list.txt; then exit 1; fi
if grep -q 'BEGIN .*PRIVATE KEY' diff.patch config; then exit 1; fi
printf '%s\n' 'GENERATED_MODULE_SIGNING_PRIVATE_KEY_NOT_IN_RPM_OR_SOURCE_PAYLOAD'
