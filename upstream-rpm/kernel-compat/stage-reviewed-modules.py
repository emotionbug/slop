#!/usr/bin/env python3
"""Stage locally held, exact QEMU-tested modules for one parallel EL8 kernel.

No vendor binaries are downloaded, changed, loaded, unloaded or redistributed.
This does not create an initramfs, change boot configuration or restart services.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

TARGET = '4.18.0-553.168.1.linuxoss1.el8_10.x86_64'
SOURCE = '4.18.0-553.166.1.el8_10.x86_64'
IMAGE_SHA = '199d5c598ba44d38277f54bf9b464cab16fe7963ea706e0b75e31a762a5b0c8c'
SYMVERS_SHA = '3aaee36520381aa761e133814ae75bf667231a625b89b1c3ad15a7ed2eee7c8e'
PROFILE = (
    ('gc_enforcement', 'gc-enforcement.ko',
     '/lib/modules/' + SOURCE + '/extra/gc-enforcement.ko',
     'e5895f7a3148497dd809408a4acb2600df900d8eb95d61e8a4ad72ead1147dad',
     'srcversion', '1E3CF09EA0054B840FB024B'),
    ('dsa_filter_hook', 'dsa_filter_hook.ko',
     '/opt/ds_agent/' + SOURCE + '/dsa_filter_hook.ko',
     '198bb5c9c11c294f7122c85a48883d7e92ad255dc997ece83064c8316cb8e45c',
     'srcversion', '533BB7E5866E52F63B9ACCB'),
    ('dsa_filter', 'dsa_filter.ko',
     '/opt/ds_agent/' + SOURCE + '/dsa_filter.ko',
     'abf6aea64fb58678d80387c2c000f5f9437e730f2a41843082c9f0130807d3b2',
     'version', '12.6.0.8491 (HUA)'),
)


def run(args):
    return subprocess.check_output(args, universal_newlines=True, stderr=subprocess.STDOUT).strip()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require_hash(path, expected):
    if digest(path) != expected:
        raise RuntimeError('Unreviewed or changed file: ' + str(path))


def copy_new_exact(source, target, expected):
    """Create one new file atomically; never overwrite a different file/symlink."""
    require_hash(source, expected)
    if target.is_symlink():
        raise RuntimeError('Destination symlink is not accepted: ' + str(target))
    if target.exists():
        require_hash(target, expected)
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.linuxoss-', dir=str(target.parent))
    temp = Path(name)
    try:
        with os.fdopen(fd, 'wb') as out, Path(source).open('rb') as src:
            for block in iter(lambda: src.read(1024 * 1024), b''):
                out.write(block)
            out.flush()
            os.fsync(out.fileno())
        require_hash(temp, expected)
        os.chmod(str(temp), 0o644)
        os.link(str(temp), str(target))  # Fails closed if another file appeared.
    finally:
        temp.unlink()
    return True


def check_live_identity(sysroot, module, field, expected):
    path = sysroot / module / field
    if not path.is_file() or path.read_text().strip() != expected:
        raise RuntimeError('Loaded module differs from the tested profile: ' + module)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('check', 'apply'), nargs='?', default='check')
    args = p.parse_args()
    if os.geteuid() != 0:
        raise RuntimeError('Run with sudo /usr/libexec/platform-python.')
    if os.uname().release != SOURCE:
        raise RuntimeError('This profile requires the unchanged source kernel: ' + SOURCE)
    with open('/run/linuxoss-install.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require_hash('/boot/vmlinuz-' + TARGET, IMAGE_SHA)
        symvers = Path('/usr/src/kernels') / TARGET / 'Module.symvers'
        require_hash(symvers, SYMVERS_SHA)
        for package in ('kernel-linuxoss-el8-compat', 'kernel-linuxoss-el8-compat-devel'):
            run(['rpm', '-V', package + '-4.18.0-553.168.1.linuxoss1.el8_10.x86_64'])
        before = run(['grubby', '--default-kernel'])
        destination = Path('/lib/modules') / TARGET / 'extra/linuxoss-reviewed'
        if destination.is_symlink():
            raise RuntimeError('Destination directory must not be a symlink')
        actual_root = (Path('/lib/modules') / TARGET).resolve()
        if actual_root not in destination.resolve().parents:
            raise RuntimeError('Destination escaped the target kernel tree')
        plan = []
        for name, filename, source, expected, field, identity in PROFILE:
            check_live_identity(Path('/sys/module'), name, field, identity)
            require_hash(source, expected)
            if run(['modinfo', '-F', 'name', source]) != name:
                raise RuntimeError('Module name mismatch: ' + source)
            target = destination / filename
            if target.is_symlink():
                raise RuntimeError('Destination module must not be a symlink')
            if target.exists():
                require_hash(target, expected)
            plan.append({'module':name,'source':source,'destination':str(target),'sha256':expected})
        print(json.dumps({'mode':args.mode,'target_kernel':TARGET,'files':plan}, indent=2))
        if args.mode == 'check':
            print('CHECK_COMPLETED_NO_CHANGES')
            return
        for item in plan:
            copy_new_exact(item['source'], Path(item['destination']), item['sha256'])
        run(['depmod', '-a', TARGET])
        for item in plan:
            selected = Path(run(['modinfo', '-k', TARGET, '-n', item['module']]))
            if selected.resolve() != Path(item['destination']).resolve():
                raise RuntimeError('depmod selected another module: ' + str(selected))
            require_hash(selected, item['sha256'])
        if run(['grubby', '--default-kernel']) != before:
            raise RuntimeError('Boot default changed unexpectedly; inspect before proceeding')
        print('STAGED_MODULES_ONLY_NO_LOAD_OR_BOOT_CHANGE')
        print('Full agent policy and target-server boot remain untested.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit('ERROR: ' + str(error))
