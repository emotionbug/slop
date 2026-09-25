#!/usr/bin/env bash
set -Eeuo pipefail
[[ $(cat /etc/hostname) == linuxoss-kernel-fixture && -f /var/lib/linuxoss-fixture/old-kernel ]] || exit 2
fail() { echo KERNEL_EL8_FIXTURE_FAILED; journalctl -b -p err --no-pager; sync; systemctl poweroff; }
trap fail ERR
state=/var/lib/linuxoss-fixture
phase=$(cat "$state/phase" 2>/dev/null || echo 0)
old=$(cat "$state/old-kernel")
kit=/opt/kernel-fixture/kit
echo "KERNEL_EL8_PHASE_${phase}_START $(uname -r)"
test "$(getenforce)" = Enforcing
systemctl is-active sshd firewalld linuxoss-fixture-java
test -d /sys/firmware/efi
test "$(findmnt -n -o FSTYPE /)" = xfs
test -e /dev/mapper/linuxoss-root
test -e /sys/class/net/eth0/device/driver
if [[ $phase == 0 ]]; then
    test "$(uname -r)" = "$old"
    before=$(rpm -qa --qf '%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\n' | LC_ALL=C sort | sha256sum)
    bash "$kit/kernel.sh" check
    test "$(rpm -qa --qf '%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\n' | LC_ALL=C sort | sha256sum)" = "$before"
    echo KERNEL_EL8_CHECK_MODE_NO_RPM_CHANGE_PASSED
    bash "$kit/kernel.sh" apply
    bash "$kit/kernel.sh" boot-once
    echo 1 > "$state/phase"
    echo KERNEL_EL8_INSTALL_AND_BOOT_ONCE_PASSED
elif [[ $phase == 1 ]]; then
    test "$(uname -r)" = 7.2.7-linuxoss+
    test "$(grubby --default-kernel)" = "/boot/vmlinuz-$old"
    ! grub2-editenv - list | grep -q '^next_entry=.'
    /usr/bin/java -version
    systemctl set-property --runtime linuxoss-fixture-java.service MemoryLimit=256M
    test "$(cat /sys/fs/cgroup/memory/system.slice/linuxoss-fixture-java.service/memory.limit_in_bytes)" = 268435456
    echo KERNEL_EL8_CGROUP_V1_MEMORY_LIMIT_PASSED
    /usr/libexec/platform-python -c 'import urllib.request; assert urllib.request.urlopen("http://127.0.0.1:8080",timeout=5).read()==b"JAVA8_KERNEL_HTTP_OK\n"'
    nft list ruleset > "$state/nft-rules.txt"
    test -s "$state/nft-rules.txt"
    echo KERNEL_EL8_WAITING_HOST_SSH_HTTP
    for ((n=0;n<120;n++)); do
        [[ ! -f $state/host-verified ]] || break
        sleep 1
    done
    test -f "$state/host-verified"
    dnf --noplugins --disablerepo='*' check
    # Exercise confirmation, then restore the old default to test fallback.
    bash "$kit/kernel.sh" confirm
    test "$(grubby --default-kernel)" = /boot/vmlinuz-7.2.7-linuxoss+
    bash "$kit/kernel.sh" fallback
    echo 2 > "$state/phase"
    echo KERNEL_EL8_UEFI_LVM_XFS_SSH_JAVA_SELINUX_NFT_PASSED
elif [[ $phase == 2 ]]; then
    test "$(uname -r)" = "$old"
    rpm -q 'kernel-7.2.7_linuxoss+-3.el8.x86_64'
    echo 3 > "$state/phase"
    echo KERNEL_EL8_OLD_DEFAULT_BOOT_PASSED
else
    exit 2
fi
sync
systemctl poweroff
