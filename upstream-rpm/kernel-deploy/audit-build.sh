#!/usr/bin/env bash
set -Eeuo pipefail
[[ -f /run/.containerenv && $# == 0 ]] || exit 2
audit=$(mktemp -d /tmp/kernel-audit.XXXXXXXX)
(cd "$audit"; rpm2cpio /output/kernel-7.2.7_linuxoss+-3.el8.src.rpm | cpio -idm --quiet --no-absolute-filenames)
tar -tzf "$audit/linux.tar.gz" > "$audit/source-files.txt"
if grep -E '(^|/)(signing_key\.pem|.*-key\.pem)$' "$audit/source-files.txt"; then exit 1; fi
for rpm in /output/kernel*-3.el8.x86_64.rpm; do
    rpm -qpl "$rpm" > "$audit/$(basename "$rpm").files.txt"
    if grep -E '(^|/)(signing_key\.pem|.*-key\.pem)$' "$audit/$(basename "$rpm").files.txt"; then exit 1; fi
done
grep -q '^CONFIG_MEMCG_V1=y$' /output/config-after
grep -q '^CONFIG_DEBUG_INFO_BTF=y$' /output/config-after
echo KERNEL_SOURCE_BINARY_PRIVATE_KEY_AND_CONFIG_AUDIT_PASSED
