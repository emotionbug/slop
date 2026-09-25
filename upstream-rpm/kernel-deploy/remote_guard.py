#!/usr/libexec/platform-python
"""A one-attempt, explicit-confirmation guard. Not a hardware watchdog."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import sys
import time

STATE = Path('/var/lib/linuxoss-kernel/remote-boot.json')
LOCK = Path('/run/linuxoss-kernel.lock')
SCRIPT = Path('/usr/local/libexec/linuxoss-kernel-guard.py')
UNIT = Path('/etc/systemd/system/linuxoss-kernel-guard.service')
SERVICE = UNIT.name
KEYS = ('panic', 'rd.shell', 'rd.emergency', 'rd.retry', 'rd.timeout', 'linuxoss.remote_boot')
ACTIVE = ('armed', 'watching', 'rolling-back')
UNIT_TEXT = '''# Managed by LinuxOSS remote kernel boot guard
[Unit]
Description=LinuxOSS one-attempt kernel confirmation deadline
DefaultDependencies=no
After=local-fs.target systemd-sysctl.service
Before=basic.target
IgnoreOnIsolate=yes
ConditionPathExists=/var/lib/linuxoss-kernel/remote-boot.json
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
ExecStart=/usr/libexec/platform-python /usr/local/libexec/linuxoss-kernel-guard.py watch
Restart=on-failure
RestartSec=3
TimeoutStopSec=10
StandardOutput=journal+console
StandardError=journal+console

[Install]
WantedBy=sysinit.target
'''


def run(args, timeout=30):
    return subprocess.check_output(args, universal_newlines=True, timeout=timeout).strip()


def load():
    return json.loads(STATE.read_text()) if STATE.exists() else None


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(state, f, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    tmp.chmod(0o600)
    os.replace(str(tmp), str(STATE))
    fd = os.open(str(STATE.parent), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def uptime():
    return float(Path('/proc/uptime').read_text().split()[0])


def token():
    values = [p.split('=', 1)[1] for p in shlex.split(Path('/proc/cmdline').read_text())
              if p.startswith('linuxoss.remote_boot=')]
    return values[0] if len(values) == 1 else None


def matches(state):
    return (state and os.uname().release == state['kernel_release']
            and token() == state['token'] and boot_id() != state['armed_from_boot_id'])


def restore_args(state):
    run(['grubby', '--update-kernel=' + state['new_kernel'],
         '--remove-args=' + ' '.join(KEYS)])
    if state['previous_args']:
        run(['grubby', '--update-kernel=' + state['new_kernel'],
             '--args=' + shlex.join(state['previous_args'])] if hasattr(shlex, 'join') else
            ['grubby', '--update-kernel=' + state['new_kernel'],
             '--args=' + ' '.join(shlex.quote(p) for p in state['previous_args'])])


def arm(manifest, deployment, entry):
    previous = load()
    if previous and previous['phase'] in ACTIVE:
        raise RuntimeError('A remote boot attempt is already active; use fallback before re-arming.')
    if os.uname().release == manifest['kernel_release']:
        raise RuntimeError('Arm the trial while running the existing fallback kernel.')
    if deployment['old_default'] != '/boot/vmlinuz-' + os.uname().release:
        raise RuntimeError('Remote trial requires the currently running kernel to be the saved fallback.')
    if re.search(r'^next_entry=.+', run(['grub2-editenv', '-', 'list']), re.M):
        raise RuntimeError('An existing one-time boot is pending; use fallback first.')
    old_initrd = '/boot/initramfs-' + os.uname().release + '.img'
    if not Path(old_initrd).is_file():
        raise RuntimeError('Fallback initramfs is missing.')
    original = shlex.split(entry['args'])
    if any(p.startswith('linuxoss.remote_boot=') for p in original):
        raise RuntimeError('Stale remote boot arguments found; use fallback before re-arming.')
    if UNIT.exists() and not UNIT.read_text().startswith('# Managed by LinuxOSS'):
        raise RuntimeError('Refusing to replace an unrelated service.')
    SCRIPT.parent.mkdir(parents=True, exist_ok=True)
    SCRIPT.write_bytes(Path(__file__).read_bytes())
    SCRIPT.chmod(0o755)
    UNIT.write_text(UNIT_TEXT)
    run(['restorecon', '-F', str(SCRIPT), str(UNIT)])
    run(['systemctl', 'daemon-reload'])
    run(['systemctl', 'enable', SERVICE])
    if run(['systemctl', 'is-enabled', SERVICE]) != 'enabled':
        raise RuntimeError('Boot guard service was not enabled.')
    state = {'schema_version': 1, 'phase': 'armed', 'token': secrets.token_hex(16),
             'kernel_release': manifest['kernel_release'], 'new_kernel': entry['kernel'],
             'old_default': deployment['old_default'], 'armed_from_boot_id': boot_id(),
             'timeout_seconds': 1200, 'armed_at': time.time(),
             'previous_args': [p for p in original if p.split('=', 1)[0] in KEYS],
             'guard_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest()}
    save(state)
    try:
        args = 'panic=60 rd.shell=0 rd.emergency=reboot rd.retry=180 rd.timeout=240 linuxoss.remote_boot=' + state['token']
        run(['grubby', '--update-kernel=' + entry['kernel'], '--remove-args=' + ' '.join(KEYS), '--args=' + args])
        run(['grubby', '--set-default=' + state['old_default']])
        if run(['grubby', '--default-kernel']) != state['old_default']:
            raise RuntimeError('Fallback default verification failed.')
        run(['grub2-reboot', entry['id']])
        if 'next_entry=' + entry['id'] not in run(['grub2-editenv', '-', 'list']).splitlines():
            raise RuntimeError('One-time boot verification failed.')
    except Exception:
        run(['grub2-editenv', '-', 'unset', 'next_entry'])
        restore_args(state)
        state['phase'] = 'cancelled'
        save(state)
        raise
    print('REMOTE_BOOT_ARMED: after reboot, confirm from SSH within 20 minutes of kernel boot.')
    print('No reboot performed. Full early boot hangs are not covered by this software guard.')


def confirmation_state():
    state = load()
    if not state or state['phase'] not in ACTIVE:
        return None
    if not matches(state) or state['phase'] != 'watching' or state.get('trial_boot_id') != boot_id():
        raise RuntimeError('The boot guard has not verified this trial boot, or rollback is already in progress.')
    if uptime() >= state['timeout_seconds']:
        raise RuntimeError('Confirmation deadline expired; allow fallback to complete.')
    return state


def confirmed(state):
    if state:
        restore_args(state)
        state['phase'] = 'confirmed'
        state['confirmed_boot_id'] = boot_id()
        state['confirmed_at'] = time.time()
        save(state)


def cancel():
    state = load()
    if state and state['phase'] in ACTIVE:
        restore_args(state)
        state['phase'] = 'cancelled'
        save(state)


def status():
    state = load()
    if state and matches(state) and state['phase'] == 'watching':
        state = dict(state, seconds_remaining=max(0, int(state['timeout_seconds'] - uptime())))
    return state


def rollback(state):
    # Never request a reboot until the old default and cleared next_entry are verified.
    run(['grub2-editenv', '-', 'unset', 'next_entry'])
    run(['grubby', '--set-default=' + state['old_default']])
    if run(['grubby', '--default-kernel']) != state['old_default']:
        raise RuntimeError('Cannot verify fallback default; refusing a possible reboot loop.')
    if re.search(r'^next_entry=.+', run(['grub2-editenv', '-', 'list']), re.M):
        raise RuntimeError('Cannot clear one-time selection; refusing a possible reboot loop.')
    state['phase'] = 'rolling-back'
    state['reason'] = 'SSH confirmation deadline expired'
    save(state)
    print('LINUXOSS_REMOTE_GUARD_TIMEOUT_REBOOT_OLD_KERNEL', flush=True)
    run(['systemctl', '--no-block', 'reboot'], timeout=15)


def watch():
    with LOCK.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load()
        if not state or state['phase'] not in ACTIVE or boot_id() == state['armed_from_boot_id']:
            return
        if os.uname().release != state['kernel_release']:
            if '/boot/vmlinuz-' + os.uname().release == state['old_default']:
                state['phase'] = 'returned-to-old-kernel'
                state['returned_boot_id'] = boot_id()
                restore_args(state)
                save(state)
                print('LINUXOSS_REMOTE_GUARD_OLD_KERNEL_RETURNED', flush=True)
            return
        if not matches(state):
            raise RuntimeError('Remote attempt token does not match the running kernel command line.')
        if state.get('trial_boot_id') and state['trial_boot_id'] != boot_id():
            raise RuntimeError('This one-attempt token was reused on a second boot.')
        run(['grub2-editenv', '-', 'unset', 'next_entry'])
        run(['grubby', '--set-default=' + state['old_default']])
        if run(['grubby', '--default-kernel']) != state['old_default']:
            raise RuntimeError('Fallback default was not retained.')
        Path('/proc/sys/kernel/panic').write_text('60\n')
        state['trial_boot_id'] = boot_id()
        if state['phase'] != 'rolling-back':
            state['phase'] = 'watching'
        save(state)
        print('LINUXOSS_REMOTE_GUARD_WATCHING: confirm before boot uptime reaches {} seconds'.format(state['timeout_seconds']), flush=True)
        fcntl.flock(lock, fcntl.LOCK_UN)
        while True:
            state = load()
            if not state or state['phase'] not in ACTIVE or not matches(state):
                return
            if uptime() >= state['timeout_seconds'] or state['phase'] == 'rolling-back':
                fcntl.flock(lock, fcntl.LOCK_EX)
                state = load()
                if state and state['phase'] in ACTIVE and matches(state):
                    rollback(state)
                else:
                    return
                fcntl.flock(lock, fcntl.LOCK_UN)
                # If orderly shutdown stalls while this process can still run,
                # escalate once. A completely stuck kernel remains uncovered.
                time.sleep(120)
                state = load()
                if not state or state['phase'] != 'rolling-back' or not matches(state):
                    return
                print('LINUXOSS_REMOTE_GUARD_FORCE_REBOOT_AFTER_SHUTDOWN_TIMEOUT', flush=True)
                run(['systemctl', '--force', 'reboot'], timeout=15)
                return
            time.sleep(2)


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] != 'watch' or os.geteuid() != 0:
        raise SystemExit('This program is the root-owned boot guard service.')
    watch()
