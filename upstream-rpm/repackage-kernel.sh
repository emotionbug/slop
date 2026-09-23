#!/usr/bin/env bash
# Repackage an already completed, hash-verified kernel build in its cache image.
set -euo pipefail
[[ $(id -u) -ne 0 && $# == 1 ]] || exit 2
tree=$(realpath -- "$1")
[[ $tree == /tmp/kernel-build.*/linux-7.2.7 && -f $tree/vmlinux && -f $tree/modules.order ]] || exit 2
cd "$tree"
git diff --exit-code HEAD -- .
[[ -f certs/signing_key.pem ]] || exit 1
export PATH="$(dirname "$tree")/bin:$PATH"
export KBUILD_BUILD_USER=linuxoss KBUILD_BUILD_HOST=isolated-builder
touch /tmp/kernel-repackage-started
make -j4 rpm-pkg RPMOPTS='--define "_smp_mflags -j4" --define "install_mod_strip 1"'
find rpmbuild -type f -name '*.rpm' -newer /tmp/kernel-repackage-started -exec cp -t /output -- {} +
cp .config System.map /output/
(cd /output && sha256sum -- ./*.rpm > SHA256SUMS)
echo KERNEL_STRIPPED_MODULE_RPMS_BUILT_REQUIRE_NEW_BOOT_TEST
