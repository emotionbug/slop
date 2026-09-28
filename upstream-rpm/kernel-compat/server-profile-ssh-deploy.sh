#!/usr/bin/env bash
# SSH-safe parallel kernel deployment. Every mode leaves the current boot alone.
set -Eeuo pipefail
umask 077
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
manifest=$here/server-profile-module-manifest-final.json
TARGET=$(/usr/libexec/platform-python -c 'import json,sys; print(json.load(open(sys.argv[1]))["release"])' "$manifest")
mode=${1:---status}
shift || true
overlay=''
if [[ $mode == --install ]]; then
  [[ $# == 2 && $1 == --profile-overlay ]] || { echo 'Use --install --profile-overlay /secure/path/overlay.tar.' >&2; exit 2; }
  overlay=$2
elif [[ $mode == --install-from-running || $mode == --check-from-running ]]; then
  [[ $# == 3 ]] || { echo "Use $mode MODULE1 MODULE2 MODULE3." >&2; exit 2; }
  [[ $1 != "$2" && $1 != "$3" && $2 != "$3" ]] || { echo 'Module names must be unique.' >&2; exit 2; }
else
  [[ $# == 0 ]] || { echo 'This mode takes no additional arguments.' >&2; exit 2; }
fi
case $mode in --status|--install|--install-from-running|--check-from-running|--arm-next-boot|--commit|--rollback) ;; *) echo 'Unsupported deployment action.' >&2; exit 2 ;; esac
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 2; }
exec 9>/run/linuxoss-install.lock
flock -n 9 || { echo 'Another kernel operation is running.' >&2; exit 2; }
# Child staging tools share this dispatcher lock and must not lock a separate
# file description for the same path.
export LINUXOSS_LOCK_HELD=1
state=/var/lib/linuxoss-kernel-compat
marker=/run/linuxoss-kernel-compat/agent-health.ok

case $mode in
  --status)
    printf 'target=%s\nrunning=%s\ndefault=%s\n' "$TARGET" "$(uname -r)" "$(grubby --default-kernel)"
    rpm -q kernel-linuxoss-el8-compat >/dev/null 2>&1 && echo rpm=installed || echo rpm=absent
    if [[ -e /dev/watchdog || -e /sys/class/watchdog/watchdog0 ]]; then echo watchdog=available; else echo watchdog=unavailable; fi
    [[ -r $marker && $(<"$marker") == healthy ]] && echo agent-health-marker=healthy || echo agent-health-marker=absent
    ;;
  --install)
    bash "$here/stage-kernel.sh" apply
    /usr/libexec/platform-python "$here/install-private-module-overlay.py" \
      --archive "$overlay" --public-key "$here/module-profile-signing-public.pem"
    /usr/libexec/platform-python "$here/stage-reviewed-modules.py" apply
    rm -f "$state/local-module-profile.json"
    echo 'INSTALL_STAGED_NO_BOOT_CHANGE_NO_REBOOT'
    ;;
  --check-from-running)
    /usr/libexec/platform-python "$here/stage-reviewed-modules.py" --local-running check "$@"
    ;;
  --install-from-running)
    bash "$here/stage-kernel.sh" apply
    /usr/libexec/platform-python "$here/stage-reviewed-modules.py" --local-running apply "$@"
    echo 'INSTALL_STAGED_FROM_RUNNING_NO_BOOT_CHANGE_NO_REBOOT'
    ;;
  --arm-next-boot)
    rpm -q kernel-linuxoss-el8-compat >/dev/null
    if [[ -s $state/local-module-profile.json ]]; then
      /usr/libexec/platform-python "$here/stage-reviewed-modules.py" --local-profile-check >/dev/null
    else
      /usr/libexec/platform-python "$here/stage-reviewed-modules.py" check >/dev/null
    fi
    bash "$here/prepare-ssh-boot.sh" apply
    echo 'ONE_SHOT_ARMED_NO_REBOOT_DEFAULT_UNCHANGED'
    ;;
  --commit)
    [[ $(uname -r) == "$TARGET" ]] || { echo 'Target kernel is not running.' >&2; exit 2; }
    [[ -r $marker && $(<"$marker") == healthy ]] || { echo 'Agent health marker is absent.' >&2; exit 2; }
    systemctl is-active --quiet sshd.service
    systemctl is-active --quiet network-online.target
    if [[ -s $state/local-module-profile.json ]]; then
      /usr/libexec/platform-python "$here/stage-reviewed-modules.py" --local-profile-check >/dev/null
    else
      /usr/libexec/platform-python "$here/stage-reviewed-modules.py" check >/dev/null
    fi
    grubby --set-default "/boot/vmlinuz-$TARGET"
    touch "$state/confirmed-$TARGET"
    systemctl disable linuxoss-boot-guard.timer >/dev/null 2>&1 || true
    echo 'PERSISTENT_DEFAULT_COMMITTED_NO_REBOOT'
    ;;
  --rollback)
    [[ -s $state/original-default-kernel ]] || { echo 'Saved original default is unavailable.' >&2; exit 2; }
    grubby --set-default "$(<"$state/original-default-kernel")"
    grub2-editenv - unset next_entry || true
    systemctl disable --now linuxoss-boot-guard.timer >/dev/null 2>&1 || true
    rm -f "$state/confirmed-$TARGET" "$state/healthy-$TARGET" "$marker"
    echo 'DEFAULT_RESTORED_PACKAGES_RETAINED_NO_REBOOT'
    ;;
esac
