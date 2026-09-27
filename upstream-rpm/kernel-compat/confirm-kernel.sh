#!/usr/bin/env bash
# Promote the trial kernel only after SSH, agents, Java and Tomcat are healthy.
set -Eeuo pipefail

TARGET='4.18.0-553.168.1.linuxoss1.el8_10.x86_64'
STATE=/var/lib/linuxoss-kernel-compat
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
[[ $(uname -r) == "$TARGET" ]] || { echo "Not running $TARGET" >&2; exit 2; }
systemctl is-active --quiet sshd.service
ip route show default | grep -q .

check_module() {
  local module=$1 field=$2 expected=$3
  [[ -r /sys/module/$module/$field ]]
  [[ $(<"/sys/module/$module/$field") == "$expected" ]]
}
check_module gc_enforcement srcversion 1E3CF09EA0054B840FB024B
check_module dsa_filter_hook srcversion 533BB7E5866E52F63B9ACCB
check_module dsa_filter version '12.6.0.8491 (HUA)'

java_pattern=${LINUXOSS_JAVA_PATTERN:-'[j]ava'}
tomcat_pattern=${LINUXOSS_TOMCAT_PATTERN:-'[o]rg.apache.catalina.startup.Bootstrap|[c]atalina'}
pgrep -af -- "$java_pattern" >/dev/null
pgrep -af -- "$tomcat_pattern" >/dev/null

grubby --set-default "/boot/vmlinuz-$TARGET"
install -d -m 0700 "$STATE"
touch "$STATE/confirmed-$TARGET"
systemctl disable --now linuxoss-boot-guard.timer >/dev/null 2>&1 || true
echo "CONFIRMED_DEFAULT_KERNEL=$TARGET"
