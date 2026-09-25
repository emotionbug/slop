#!/usr/libexec/platform-python
"""Install one pinned kernel alongside existing kernels; never reboot or erase."""
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

STATE = Path('/var/lib/linuxoss-kernel')


def run(args, **kwargs):
    print('+ ' + ' '.join(str(a) for a in args), flush=True)
    return subprocess.check_output([str(a) for a in args], universal_newlines=True, **kwargs).strip()


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def entry(kernel):
    text = run(['grubby', '--info=' + str(kernel)])
    values = {}
    for line in text.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            values[key] = value.strip('"')
    if not values.get('id') or values.get('kernel') != str(kernel):
        raise RuntimeError('Cannot identify exactly one boot entry for ' + str(kernel))
    return values


def preflight(root, report, manifest):
    if Path('/run/.containerenv').exists() or Path('/.dockerenv').exists():
        raise RuntimeError('Run kernel operations on the host, not in a container.')
    if not Path('/sys/firmware/efi').is_dir():
        raise RuntimeError('This tested installer requires the UEFI/BLS layout.')
    fips = Path('/proc/sys/crypto/fips_enabled')
    if fips.exists() and fips.read_text().strip() == '1':
        raise RuntimeError('FIPS mode requires a validated kernel/crypto stack; this upstream image cannot replace that contract.')
    variables = list(Path('/sys/firmware/efi/efivars').glob('SecureBoot-*'))
    if len(variables) != 1 or len(variables[0].read_bytes()) != 5:
        raise RuntimeError('Cannot determine UEFI Secure Boot state.')
    if variables[0].read_bytes()[4] != 0:
        raise RuntimeError('Secure Boot is enabled: enroll a kernel signing key and sign the image before deployment. No firmware setting was changed.')
    if not Path('/boot/loader/entries').is_dir():
        raise RuntimeError('BLS boot entries are missing; bootloader integration needs repair first.')
    running = os.uname().release
    old = run(['grubby', '--default-kernel'])
    if not Path(old).is_file() or not Path('/boot/vmlinuz-' + running).is_file():
        raise RuntimeError('The running/default fallback kernel image is missing.')
    old_entry = entry(old)
    machine_id = Path('/etc/machine-id').read_text().strip()
    if not re.fullmatch(r'[0-9a-f]{32}', machine_id):
        raise RuntimeError('Invalid machine-id; repair the host identity and BLS entries before kernel installation.')
    if not old_entry['id'].startswith(machine_id + '-'):
        raise RuntimeError('Fallback BLS entry belongs to another machine-id. Align a fallback BLS copy with the current machine-id before installation; no RPM was changed.')
    if not old.startswith('/boot/vmlinuz-') or not Path('/boot/initramfs-' + old[len('/boot/vmlinuz-'):] + '.img').is_file():
        raise RuntimeError('Default fallback initramfs is missing.')
    env = run(['grub2-editenv', '-', 'list'])
    if re.search(r'^next_entry=.+', env, re.M):
        raise RuntimeError('A one-time boot is already pending; retain it and resolve it before installation.')
    if shutil.disk_usage('/boot').free < 350 * 1024 ** 2 or shutil.disk_usage('/usr/lib/modules').free < 1024 ** 3:
        raise RuntimeError('Need at least 350 MiB free in /boot and 1 GiB in the modules filesystem.')
    external = []
    for line in Path('/proc/modules').read_text().splitlines():
        name = line.split()[0]
        p = subprocess.run(['modinfo', '-F', 'intree', name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if p.returncode or p.stdout.strip() != 'Y':
            external.append(name)
    if external:
        save(report / 'external-modules.json', external)
        raise RuntimeError('Active external modules need a 7.2.7 rebuild: ' + ', '.join(external))
    xfs = []
    mounts = run(['findmnt', '-rn', '-t', 'xfs', '-o', 'TARGET']).splitlines()
    for target in mounts:
        text = run(['xfs_info', target])
        xfs.append({'mount': target, 'info': text})
        if not re.search(r'\bcrc=1\b', text) or re.search(r'\bascii-ci=1\b', text):
            raise RuntimeError('XFS V4/case-insensitive filesystem requires a compatibility kernel build; this image must not be booted on it.')
    drivers = {'vmw_pvscsi', 'vmxnet3', 'sd_mod', 'xfs', 'dm_mod', 'ext4'}
    for path in Path('/sys/bus/pci/devices').glob('*/driver/module'):
        drivers.add(path.resolve().name)
    config = run(['dmsetup', 'table', '--target', 'vdo'])
    if config:
        raise RuntimeError('Active VDO volumes require a VDO-enabled kernel and metadata compatibility verification.')
    with tempfile.TemporaryDirectory(prefix='linuxoss-kernel-inspect-') as folder:
        core = root / next(p['path'] for p in manifest['rpms'] if p['name'] == 'kernel')
        child = subprocess.Popen(['rpm2cpio', str(core)], stdout=subprocess.PIPE)
        subprocess.run(['cpio', '-idm', '--quiet', '--no-absolute-filenames'], cwd=folder, stdin=child.stdout, check=True)
        child.stdout.close()
        if child.wait():
            raise RuntimeError('Kernel payload extraction failed.')
        # Upstream rpm-pkg defers depmod indices to installation. Generate them
        # only inside the temporary payload so EL8 kmod can resolve aliases.
        run(['depmod', '-b', folder, '-a', manifest['kernel_release']])
        module_root = Path(folder) / 'lib/modules' / manifest['kernel_release']
        builtins = {Path(p).stem.replace('-', '_') for p in (module_root / 'modules.builtin').read_text().splitlines()}
        builtin_drivers = sorted(drivers & builtins)
        for driver in sorted(drivers):
            # EL8 modinfo cannot report built-ins from newer kernels. Verify
            # their exact RPM-pinned modules.builtin entries instead; they do
            # not belong in dracut's list of loadable drivers.
            if driver in builtins:
                continue
            run(['modinfo', '-b', folder, '-k', manifest['kernel_release'], driver])
    result = {'running_kernel': running, 'old_default': old, 'old_entry': old_entry,
              'grub_environment': env, 'required_drivers': sorted(drivers - builtins), 'builtin_drivers': builtin_drivers, 'xfs': xfs,
              'external_modules': external, 'secure_boot': 'disabled'}
    save(report / 'preflight.json', result)
    return result


def install(mode, root, report, manifest):
    import dnf
    info = preflight(root, report, manifest)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    with dnf.Base() as base:
        base.conf.read()
        base.conf.plugins = False
        base.conf.install_weak_deps = False
        base.conf.clean_requirements_on_remove = False
        base.conf.localpkg_gpgcheck = False
        base.conf.obsoletes = False
        base.conf.installonly_limit = 0
        base.conf.installonlypkgs = list(set(base.conf.installonlypkgs) | {'kernel', 'kernel-devel'})
        base.conf.cachedir = str(report / 'dnf-cache')
        base.conf.logdir = str(report)
        base.conf.tsflags = []
        base.fill_sack(load_system_repo=True, load_available_repos=False)
        candidates = base.add_remote_rpms([str(root / x['path']) for x in manifest['rpms']], strict=True)
        installed = list(base.sack.query().installed())
        for package in candidates:
            if not any(str(old) == str(package) for old in installed):
                base.package_install(package, strict=True)
        changed = base.resolve(allow_erasing=False)
        incoming = list(base.transaction.install_set) if changed else []
        outgoing = list(base.transaction.remove_set) if changed else []
        plan = {'install': [str(p) for p in incoming], 'remove': [str(p) for p in outgoing]}
        save(report / 'transaction.json', plan)
        if outgoing or any(p not in candidates for p in incoming):
            raise RuntimeError('Kernel transaction may only add these two pinned RPMs; replacement/removal is refused.')
        if mode == 'check':
            if changed:
                base.conf.tsflags = ['test']
                base.do_transaction()
            print('CHECK_PASSED_NO_INSTALL')
            return
        STATE.mkdir(parents=True, exist_ok=True)
        state_file = STATE / (manifest['kernel_release'] + '.json')
        if state_file.exists():
            previous = json.loads(state_file.read_text())
            if previous['kernel_release'] != manifest['kernel_release']:
                raise RuntimeError('Saved deployment identity mismatch.')
            info['old_default'] = previous['old_default']
        state = dict(info, kernel_release=manifest['kernel_release'], manifest_sha256=sha(root / 'kernel-manifest.json'), ready=False)
        save(state_file, state)
        with tempfile.TemporaryDirectory(prefix='linuxoss-kernel-boot-backup-') as tmp:
            # Only small boot metadata is backed up; old images and initrds stay installed.
            run(['tar', '-czf', report / 'boot-entries-before.tar.gz', '-C', '/boot', 'loader/entries'])
        try:
            if changed:
                base.do_transaction()
            kver = manifest['kernel_release']
            run(['depmod', '-a', kver])
            image = Path('/boot/initramfs-' + kver + '.img')
            run(['dracut', '--force', '--kver', kver, '--add-drivers', ' '.join(info['required_drivers']), str(image)])
            listing = run(['lsinitrd', str(image)])
            (report / 'initramfs-contents.txt').write_text(listing + '\n')
            for driver in ('vmw_pvscsi', 'vmxnet3', 'xfs', 'dm_mod'):
                if driver in info['builtin_drivers']:
                    continue
                # Match a module payload, not the --add-drivers text printed
                # in lsinitrd's header. dm_mod's filename is dm-mod.ko.
                pattern = r'/' + re.escape(driver).replace('_', '[-_]') + r'\.ko(?:\.(?:gz|xz|zst))?(?:\s|$)'
                if not re.search(pattern, listing, re.M):
                    raise RuntimeError('Required driver absent from initramfs: ' + driver)
            kernel = '/boot/vmlinuz-' + kver
            try:
                entry(kernel)
            except subprocess.CalledProcessError:
                run(['grubby', '--add-kernel=' + kernel, '--initrd=' + str(image), '--title=LinuxOSS ' + kver, '--copy-default'])
            state['new_entry'] = entry(kernel)
        finally:
            run(['grubby', '--set-default=' + info['old_default']])
        if run(['grubby', '--default-kernel']) != info['old_default']:
            raise RuntimeError('Fallback default restoration did not take effect.')
        state['ready'] = True
        save(state_file, state)
        print('KERNEL_INSTALLED_OLD_DEFAULT_RETAINED; next: sudo bash kernel.sh boot-once')


def main():
    mode, folder, output = sys.argv[1:4]
    root, report = Path(folder).resolve(), Path(output)
    manifest = json.loads((root / 'kernel-manifest.json').read_text())
    kver = manifest['kernel_release']
    if kver != '7.2.7-linuxoss+' or len(manifest['rpms']) != 2:
        raise RuntimeError('Unexpected kernel bundle.')
    for item in manifest['rpms']:
        path = root / item['path']
        if path.is_symlink() or sha(path) != item['sha256']:
            raise RuntimeError('Kernel RPM hash mismatch.')
    if mode in ('check', 'apply'):
        return install(mode, root, report, manifest)
    state_file = STATE / (kver + '.json')
    if not state_file.exists():
        raise RuntimeError('No saved deployment state; install the bundle first.')
    state = json.loads(state_file.read_text())
    if state['manifest_sha256'] != sha(root / 'kernel-manifest.json'):
        raise RuntimeError('Deployment manifest changed.')
    if mode == 'status':
        print(json.dumps({'running': os.uname().release, 'default': run(['grubby', '--default-kernel']),
                          'environment': run(['grub2-editenv', '-', 'list']), 'fallback': state['old_default']}, indent=2))
    elif mode == 'boot-once':
        if not state.get('ready') or sha(Path('/boot/vmlinuz-' + kver)) != manifest['kernel_image_sha256']:
            raise RuntimeError('Kernel deployment was incomplete or the installed image changed.')
        new = entry('/boot/vmlinuz-' + kver)
        run(['grubby', '--set-default=' + state['old_default']])
        run(['grub2-reboot', new['id']])
        env = run(['grub2-editenv', '-', 'list'])
        if 'next_entry=' + new['id'] not in env.splitlines():
            raise RuntimeError('One-time boot was not recorded.')
        print('ONE_TIME_BOOT_ARMED; reboot manually when ready. No automatic reboot performed.')
    elif mode == 'confirm':
        if os.uname().release != kver:
            raise RuntimeError('Boot the new kernel before confirming it.')
        run(['grub2-editenv', '-', 'unset', 'next_entry'])
        run(['grubby', '--set-default=/boot/vmlinuz-' + kver])
        print('NEW_KERNEL_SET_AS_DEFAULT')
    elif mode == 'fallback':
        if not Path(state['old_default']).is_file():
            raise RuntimeError('Saved fallback image is missing.')
        run(['grub2-editenv', '-', 'unset', 'next_entry'])
        run(['grubby', '--set-default=' + state['old_default']])
        print('OLD_KERNEL_SET_AS_DEFAULT; reboot manually if needed.')
    else:
        raise RuntimeError('Unsupported action.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        sys.exit(2)
