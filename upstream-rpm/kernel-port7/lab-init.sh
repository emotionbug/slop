#!/bin/sh
# Private isolated QEMU fixture, no disk or network attached.
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
mount -t proc proc /proc
grep -q 'linuxoss.portlab7=1' /proc/cmdline || exit 2
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /run/netns /tmp
fail() { echo PORTLAB7_FIXTURE_FAILED; dmesg | tail -n 100; sync; poweroff -f; }
trap fail EXIT
set -ex
test "$(uname -r)" = 7.2.7-linuxoss-portlab1
insmod /compat/linuxoss_legacy_strings.ko
grep -q '^linuxoss_legacy_strings ' /proc/modules
dmesg | grep 'PORTLAB7_LEGACY_STRING_SELFTEST_PASSED'
/usr/sbin/ip link set lo up
/usr/sbin/ip link add lxprobe0 type veth peer name lxprobe1
/usr/sbin/ip addr add 10.99.1.1/24 dev lxprobe0
/usr/sbin/ip link set lxprobe0 up
/usr/sbin/ip netns add sender
/usr/sbin/ip link set lxprobe1 netns sender
/usr/sbin/ip -n sender link set lo up
/usr/sbin/ip -n sender addr add 10.99.1.2/24 dev lxprobe1
/usr/sbin/ip -n sender link set lxprobe1 up
/usr/sbin/ip netns exec sender ping -c 3 -W 2 10.99.1.1
/usr/bin/security-net-smoke
/usr/sbin/ip netns del sender
/usr/sbin/ip link del lxprobe0 2>/dev/null || :
echo PORTLAB7_NATIVE_NETWORK_PASSED
/usr/sbin/ip link add br0 type bridge
/usr/sbin/ip addr add 10.99.0.1/24 dev br0
/usr/sbin/ip link set br0 up
/usr/sbin/ip link add veth0 type veth peer name veth1
/usr/sbin/ip link set veth0 master br0
/usr/sbin/ip link set veth0 up
/usr/sbin/ip netns add sender
/usr/sbin/ip link set veth1 netns sender
/usr/sbin/ip -n sender link set lo up
/usr/sbin/ip -n sender addr add 10.99.0.2/24 dev veth1
/usr/sbin/ip -n sender link set veth1 up
nft add table bridge linuxoss
nft 'add chain bridge linuxoss input { type filter hook input priority 0; policy accept; }'
nft add rule bridge linuxoss input ether type ip queue num 0
timeout 30 /usr/bin/nfqueue-bridge-test
echo PORTLAB7_NFQUEUE_LIFECYCLE_PASSED
# The admission test must continue to reject unsupported binaries. This is
# negative coverage, NEVER a successful vendor module/agent compatibility test.
for module in dsa_filter_hook dsa_filter gc-enforcement; do
    if insmod "/private-modules/$module.ko"; then
        echo "PORTLAB7_UNEXPECTED_VENDOR_MODULE_ADMISSION $module"
        exit 1
    fi
    echo "PORTLAB7_INCOMPATIBLE_MODULE_REJECTED $module"
done
rmmod linuxoss_legacy_strings
if dmesg | grep -E 'BUG:|Oops:|KASAN:|UBSAN:|general protection fault|kernel BUG|WARNING: CPU'; then exit 1; fi
echo PORTLAB7_FIXTURE_PASSED
trap - EXIT
sync
poweroff -f
