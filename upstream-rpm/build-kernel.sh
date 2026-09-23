#!/usr/bin/env bash
# Kernel RPM candidate build only; no target installation or bootloader changes.
set -euo pipefail
[[ $# == 1 && -r $1 ]] || { echo 'Usage: build-kernel.sh /inventory/config-RUNNING_KERNEL' >&2; exit 2; }
[[ $(id -u) -ne 0 ]] || { echo 'Unprivileged build required' >&2; exit 2; }
python3.11 - /recipe/sources.lock.json /sources/linux-7.2.7.tar.xz <<'PY'
import hashlib,json,sys,pathlib
p=pathlib.Path(sys.argv[2]);expected=next(r['sha256'] for r in json.load(open(sys.argv[1]))['sources'] if r['name']==p.name)
if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise SystemExit('Kernel source hash mismatch')
PY
workspace=$(mktemp -d /tmp/kernel-build.XXXXXX)
tar -xJf /sources/linux-7.2.7.tar.xz -C "$workspace"
cd "$workspace/linux-7.2.7"
# The upstream rpm-pkg target archives tracked source files. Seed a local
# repository from the hash-verified release, without adding host metadata.
git init -q
git add .
git -c user.name='Linux OSS build' -c user.email='build@localhost' \
  commit -q --no-gpg-sign -m 'Import hash-verified Linux 7.2.7 release'
cp -- "$1" .config
cp .config /output/config-before
# Red Hat's certificate is unavailable in upstream sources. Keep module signing
# enabled with the build's own generated key; no Red Hat signature is claimed.
scripts/config --set-str SYSTEM_TRUSTED_KEYS '' --set-str SYSTEM_REVOCATION_KEYS '' \
  --set-str EFI_SBAT_FILE '' --set-str LOCALVERSION '-linuxoss' --disable LOCALVERSION_AUTO
# The exported RHEL config references its distributor-owned kernel.sbat file.
# Upstream explicitly leaves SBAT policy to the signing distributor. This
# unsigned evaluation build must not copy or impersonate Red Hat SBAT identity.
mkdir -p "$workspace/bin"
ln -s /usr/bin/python3.11 "$workspace/bin/python3"
export PATH="$workspace/bin:$PATH"
export KBUILD_BUILD_USER=linuxoss KBUILD_BUILD_HOST=isolated-builder
make olddefconfig
cp .config /output/config-after
scripts/diffconfig /output/config-before /output/config-after > /output/config-diff.txt
for required in CONFIG_VMWARE_PVSCSI CONFIG_VMXNET3 CONFIG_XFS_FS CONFIG_BLK_DEV_DM CONFIG_EFI CONFIG_EFI_STUB CONFIG_BLK_DEV_INITRD; do
  grep -Eq "^${required}=(y|m)$" .config || { echo "Missing required boot/driver option: $required" >&2; exit 1; }
done
grep -q '^CONFIG_DEBUG_INFO_BTF=y$' .config
pahole --version
jobs=${BUILD_JOBS:-8}
[[ $jobs =~ ^[1-9][0-9]*$ ]] || exit 2
trap 'printf "%s\n" "$?" > /output/build-exit-code.txt' EXIT
make -j"$jobs" bzImage KBUILD_BUILD_VERSION=1
# Drop module DWARF debug sections before signing/packaging. Keep BTF and all
# configured drivers; full unstripped build files remain in the build container.
make -j"$jobs" rpm-pkg RPMOPTS="--define \"_smp_mflags -j$jobs\" --define \"install_mod_strip 1\""
find rpmbuild -type f -name '*.rpm' -exec cp -t /output -- {} +
cp .config System.map /output/
find . -name '*.ko' -printf '%P\n' | sort > /output/built-modules.txt
(cd /output && sha256sum -- ./*.rpm > SHA256SUMS)
echo 'KERNEL_RPMS_BUILT_BOOT_NOT_TESTED'
