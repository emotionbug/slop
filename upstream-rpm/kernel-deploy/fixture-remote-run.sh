#!/usr/bin/env bash
# Fault injection is allowed only inside the explicitly named disposable VM.
set -Eeuo pipefail
[[ $(cat /etc/hostname) == linuxoss-kernel-fixture && -f /var/lib/linuxoss-fixture/old-kernel ]] || exit 2
fail() { echo KERNEL_EL8_FIXTURE_FAILED; journalctl -b -p err --no-pager; sync; systemctl poweroff; }
trap fail ERR
state=/var/lib/linuxoss-fixture
phase=$(cat "$state/phase" 2>/dev/null || echo 0)
old=$(cat "$state/old-kernel")
kit=/opt/kernel-fixture/kit
guard=/var/lib/linuxoss-kernel/remote-boot.json
guard_phase() { /usr/libexec/platform-python -c 'import json; print(json.load(open("/var/lib/linuxoss-kernel/remote-boot.json"))["phase"])'; }
echo "KERNEL_REMOTE_PHASE_${phase}_START $(uname -r)"
test "$(getenforce)" = Enforcing
systemctl is-active sshd firewalld linuxoss-fixture-java
case "$phase" in
0)
    test "$(uname -r)" = "$old"
    mkdir -p /var/log/linuxoss-kernel
    sha256sum "$kit/kernel.py" "$kit/kernel.sh" "$kit/remote_guard.py" > /var/log/linuxoss-kernel/tested-control-files.sha256
    bash "$kit/kernel.sh" apply
    # Simulate an RPM update that selected a not-yet-booted kernel as default.
    grubby --set-default=/boot/vmlinuz-7.2.7-linuxoss+
    /usr/libexec/platform-python -c 'import json; p="/var/lib/linuxoss-kernel/7.2.7-linuxoss+.json"; s=json.load(open(p)); s["old_default"]="/boot/vmlinuz-7.2.7-linuxoss+"; json.dump(s,open(p,"w"))'
    bash "$kit/kernel.sh" boot-once-remote
    test "$(guard_phase)" = armed
    test "$(grubby --default-kernel)" = "/boot/vmlinuz-$old"
    echo KERNEL_REMOTE_RUNNING_KERNEL_SELECTED_AS_FALLBACK
    echo 1 > "$state/phase"
    echo KERNEL_REMOTE_INSTALL_AND_ARM_PASSED
    ;;
1)
    test "$(uname -r)" = 7.2.7-linuxoss+
    test "$(guard_phase)" = watching
    test "$(cat /proc/sys/kernel/panic)" = 60
    test "$(grubby --default-kernel)" = "/boot/vmlinuz-$old"
    ! grub2-editenv - list | grep -q '^next_entry=.'
    echo KERNEL_EL8_WAITING_HOST_SSH_HTTP
    for ((n=0;n<120;n++)); do
        [[ ! -f $state/host-verified ]] || break
        sleep 1
    done
    test -f "$state/host-verified"
    test "$(guard_phase)" = confirmed
    test "$(grubby --default-kernel)" = /boot/vmlinuz-7.2.7-linuxoss+
    ! grubby --info=/boot/vmlinuz-7.2.7-linuxoss+ | grep -q linuxoss.remote_boot
    sleep 3
    ! systemctl is-active --quiet linuxoss-kernel-guard.service
    bash "$kit/kernel.sh" fallback
    echo 2 > "$state/phase"
    echo KERNEL_REMOTE_SSH_CONFIRM_CANCELS_DEADLINE_PASSED
    ;;
2)
    test "$(uname -r)" = "$old"
    bash "$kit/kernel.sh" boot-once-remote
    # Shorten this disposable VM test only; the distributed default stays 1200s.
    /usr/libexec/platform-python -c 'import json; p="/var/lib/linuxoss-kernel/remote-boot.json"; s=json.load(open(p)); assert s["timeout_seconds"]==1200; s["timeout_seconds"]=180; json.dump(s,open(p,"w"))'
    echo 3 > "$state/phase"
    echo KERNEL_REMOTE_NO_CONFIRM_TRIAL_ARMED
    ;;
3)
    test "$(uname -r)" = 7.2.7-linuxoss+
    test "$(guard_phase)" = watching
    systemctl stop sshd
    ! systemctl is-active --quiet sshd
    echo 4 > "$state/phase"
    sync
    echo KERNEL_REMOTE_SSH_STOPPED_NO_CONFIRMATION
    sleep 600
    false
    ;;
4)
    test "$(uname -r)" = "$old"
    test "$(guard_phase)" = returned-to-old-kernel
    test "$(grubby --default-kernel)" = "/boot/vmlinuz-$old"
    echo KERNEL_REMOTE_TIMEOUT_RETURNED_OLD_PASSED
    bash "$kit/kernel.sh" boot-once-remote
    echo 5 > "$state/phase"
    echo KERNEL_REMOTE_PANIC_TRIAL_ARMED
    ;;
5)
    test "$(uname -r)" = 7.2.7-linuxoss+
    test "$(guard_phase)" = watching
    test "$(cat /proc/sys/kernel/panic)" = 60
    echo 6 > "$state/phase"
    sync
    echo KERNEL_REMOTE_INJECTING_PANIC_IN_DISPOSABLE_VM
    echo c > /proc/sysrq-trigger
    false
    ;;
6)
    test "$(uname -r)" = "$old"
    test "$(guard_phase)" = returned-to-old-kernel
    test "$(grubby --default-kernel)" = "/boot/vmlinuz-$old"
    ! grub2-editenv - list | grep -q '^next_entry=.'
    echo 7 > "$state/phase"
    echo KERNEL_REMOTE_PANIC_RETURNED_OLD_PASSED
    ;;
*) exit 2;;
esac
sync
systemctl poweroff
