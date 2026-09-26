#!/bin/sh
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
mount -t proc proc /proc
grep -q 'linuxoss.server_module_fixture=1' /proc/cmdline || exit 2
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /run/netns /tmp
fail() { echo SERVER_MODULE_FIXTURE_FAILED; dmesg | tail -n 100; sync; poweroff -f; }
trap fail EXIT
set -ex
uname -r
modprobe bridge
modprobe veth
modprobe nf_tables
modprobe nft_queue
modprobe nfnetlink_queue
modprobe nf_conntrack
/usr/sbin/ip link set lo up
# Exact unmodified server payloads. No force-vermagic or force-modversion.
insmod /private-modules/dsa_filter_hook.ko
insmod /private-modules/dsa_filter.ko
insmod /private-modules/gc-enforcement.ko
lsmod
grep -q '^gc_enforcement ' /proc/modules
grep -q '^dsa_filter ' /proc/modules
grep -q '^dsa_filter_hook ' /proc/modules
cat /sys/module/gc_enforcement/srcversion
echo SERVER_MODULES_SIMULTANEOUS_LOAD_PASSED
# Packet and device lifecycle smoke while both vendors' modules are resident.
/usr/sbin/ip -details link show
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
rmmod gc_enforcement
rmmod dsa_filter
rmmod dsa_filter_hook
if dmesg | grep -E 'BUG:|Oops:|KASAN:|general protection fault|kernel BUG|WARNING: CPU'; then exit 1; fi
echo SERVER_MODULE_LOAD_NETWORK_UNLOAD_PASSED
trap - EXIT
sync
poweroff -f
