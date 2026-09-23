#!/usr/bin/env bash
# Run only in the disposable, unprivileged kernel-boot-test container.
# Generic UEFI/VMware-device emulation, not a target-server clone.
set -euo pipefail
[[ $(id -u) -ne 0 && $# == 1 && $1 == *.rpm ]] || exit 2
[[ -e /run/.containerenv || -e /.dockerenv ]] || exit 2
work=$(mktemp -d /tmp/kernel-boot.XXXXXX)
root=$work/rpmroot
guest=$work/guest
mkdir -p "$root" "$guest"/{bin,dev,proc,sys,tmp,mnt,lib/modules}
(cd "$root" && rpm2cpio "$1" | cpio -idm --quiet --no-absolute-filenames)
mapfile -t kernels < <(find "$root/boot" -maxdepth 1 -type f -name 'vmlinuz-*')
[[ ${#kernels[@]} == 1 ]] || { echo 'Expected one kernel image' >&2; exit 1; }
kernel=${kernels[0]}
release=${kernel##*/vmlinuz-}
[[ $release == 7.2.7*linuxoss* ]] || exit 1
depmod -b "$root" -F "$root/boot/System.map-$release" "$release"
for driver in vmw_pvscsi vmxnet3 sd_mod xfs dm_mod; do
  modprobe --show-depends -d "$root" -S "$release" "$driver"
done > "$work/module-dependencies.txt"
while read -r operation module rest; do
  [[ $operation == insmod ]] || continue
  [[ $module == "$root"/* && -f $module ]] || exit 1
  relative=${module#"$root"/}
  target=$guest/$relative
  mkdir -p "$(dirname "$target")"
  case "$module" in
    *.xz) xz -dc "$module" > "${target%.xz}" ;;
    *.zst) zstd -q -dc "$module" > "${target%.zst}" ;;
    *.gz) gzip -dc "$module" > "${target%.gz}" ;;
    *.ko) cp "$module" "$target" ;;
    *) echo "Unsupported module format: $module" >&2; exit 1 ;;
  esac
done < "$work/module-dependencies.txt"
for name in modules.builtin modules.builtin.modinfo modules.order; do
  if [[ -f $root/lib/modules/$release/$name ]]; then
    cp "$root/lib/modules/$release/$name" "$guest/lib/modules/$release/"
  fi
done
depmod -b "$guest" -F "$root/boot/System.map-$release" "$release"
cp /usr/bin/busybox "$guest/bin/"
for applet in sh mount umount mkdir sleep cat cmp ip modprobe poweroff sync uname; do
  ln -s busybox "$guest/bin/$applet"
done
cat > "$guest/init" <<'INIT'
#!/bin/sh
export PATH=/bin
fail() { echo KERNEL_GENERIC_BOOT_FAILED; sync; poweroff -f; }
trap fail EXIT
set -eu
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev
echo KERNEL_GENERIC_BOOT_STARTED
uname -a
test -d /sys/firmware/efi
echo GENERIC_UEFI_BOOT_OK
modprobe vmw_pvscsi
modprobe vmxnet3
modprobe sd_mod
modprobe xfs
modprobe dm_mod
attempt=0
while [ ! -b /dev/sda ] && [ "$attempt" -lt 20 ]; do
  sleep 1
  attempt=$((attempt+1))
done
test -b /dev/sda
mount -t xfs /dev/sda /mnt
echo linuxoss-kernel-storage-check > /mnt/check
echo linuxoss-kernel-storage-check > /tmp/check
sync
cmp /tmp/check /mnt/check
umount /mnt
ip link set eth0 up
cat /sys/class/net/eth0/device/vendor
test -d /sys/class/net/eth0/device/driver
test -c /dev/mapper/control
echo KERNEL_GENERIC_UEFI_PVSCSI_XFS_VMXNET3_DM_OK
trap - EXIT
sync
poweroff -f
INIT
chmod 0755 "$guest/init"
(cd "$guest" && find . -print0 | cpio --null -o -H newc --quiet | gzip -1 > "$work/initramfs.gz")
mkfs.xfs -f -d "file,name=$work/disk.raw,size=512m" > "$work/mkfs.log"
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$work/vars.fd"
set +e
timeout 240 qemu-system-x86_64 -accel tcg -machine q35 -cpu max -smp 2 -m 2048 \
  -nodefaults -display none -monitor none -serial stdio -no-reboot \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
  -drive "if=pflash,format=raw,file=$work/vars.fd" \
  -kernel "$kernel" -initrd "$work/initramfs.gz" \
  -append 'console=ttyS0 rdinit=/init panic=-1' \
  -device pvscsi,id=scsi0 \
  -drive "file=$work/disk.raw,if=none,id=disk0,format=raw" \
  -device scsi-hd,drive=disk0,bus=scsi0.0 \
  -netdev user,id=net0 -device vmxnet3,netdev=net0 \
  > "$work/serial.log" 2>&1
code=$?
set -e
cat "$work/serial.log"
mkdir -p /output
cp "$work/serial.log" /output/kernel-generic-boot.log
cp "$work/module-dependencies.txt" /output/kernel-generic-boot-module-dependencies.txt
printf '%s\n' "$code" > /output/kernel-generic-boot-qemu-exit.txt
[[ $code == 0 ]]
grep -q '^KERNEL_GENERIC_UEFI_PVSCSI_XFS_VMXNET3_DM_OK' "$work/serial.log"
if grep -q 'KERNEL_GENERIC_BOOT_FAILED' "$work/serial.log"; then exit 1; fi
echo 'GENERIC_EMULATED_BOOT_PASSED_TARGET_JAVA_AGENTS_NOT_TESTED'
