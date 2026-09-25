#!/usr/bin/env bash
# Resume the exact source tree retained in a disposable build cache.
set -Eeuo pipefail
[[ $(id -u) != 0 && $# == 1 ]] || exit 2
while [[ -f /output/resume-hold ]]; do sleep 1; done
tree=$(realpath "$1")
[[ $tree == /tmp/kernel-build.*/linux-7.2.7 && -f $tree/.config ]] || exit 2
cd "$tree"
git diff --exit-code HEAD -- .
export PATH="$(dirname "$tree")/bin:$PATH"
export KBUILD_BUILD_USER=linuxoss KBUILD_BUILD_HOST=isolated-builder
trap 'printf "%s\n" "$?" > /output/build-exit-code.txt' EXIT
make olddefconfig
cp .config /output/config-after
grep -q '^CONFIG_MEMCG_V1=y$' .config
grep -q '^CONFIG_DEBUG_INFO_BTF=y$' .config
ld --version | head -n1
printf '%s\n' 2 > .version
# mkspec reads scripts/build-version (.version + 1), not KBUILD_BUILD_VERSION.
touch scripts/package/mkspec
# Compiler command changes cause Kbuild to rebuild the affected objects.
make -j6 rpm-pkg KBUILD_BUILD_VERSION=3 RPMOPTS='--define "_smp_mflags -j6" --define "install_mod_strip 1"'
find rpmbuild -type f -name '*-3.el8.*rpm' -exec cp -t /output -- {} +
cp .config System.map /output/
(cd /output && sha256sum ./*.rpm > SHA256SUMS)
echo KERNEL_RELEASE_3_RPMS_BUILT
