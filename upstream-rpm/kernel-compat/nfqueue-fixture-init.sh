#!/bin/sh
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
mount -t proc proc /proc
grep -q 'linuxoss.nfqueue_fixture=1' /proc/cmdline || exit 2
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /run/netns /tmp
fail() { echo NFQUEUE_FIXTURE_FAILED; dmesg | tail -n 80; sync; poweroff -f; }
trap fail EXIT
set -ex
uname -r
modprobe bridge
modprobe veth
modprobe nf_tables
modprobe nft_queue
modprobe nfnetlink_queue
# EL8 links CONFIG_NF_TABLES_BRIDGE=y into nf_tables, without a separate .ko.
/usr/sbin/ip link set lo up
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
if dmesg | grep -E 'BUG:|Oops:|KASAN:|general protection fault|kernel BUG'; then exit 1; fi
echo NFQUEUE_FIXTURE_PASSED
if [ -f /security-modules/dsa_filter_hook.ko ]; then
    insmod /security-modules/dsa_filter_hook.ko
    insmod /security-modules/dsa_filter.ko
    lsmod
    grep -q '^dsa_filter ' /proc/modules
    grep -q '^dsa_filter_hook ' /proc/modules
    rmmod dsa_filter
    rmmod dsa_filter_hook
    if dmesg | grep -E 'BUG:|Oops:|KASAN:|general protection fault|kernel BUG'; then exit 1; fi
    echo TREND_MICRO_PAIR_LOAD_UNLOAD_PASSED
fi
trap - EXIT
sync
poweroff -f
