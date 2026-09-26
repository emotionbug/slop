#!/usr/bin/env python3
"""Create an isolated initramfs for the NFQUEUE regression; never touch host /boot."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--modules', type=Path, required=True)
    p.add_argument('--kernel-release', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--security-module-dir', type=Path,
                   help='Optional local-only official Trend Micro pair; never redistributed')
    args = p.parse_args()
    if not Path('/run/.containerenv').exists():
        raise SystemExit('Run in the dedicated build container')
    root = args.output.resolve()
    if not str(root).startswith('/lab/'):
        raise SystemExit('Fixture must be created under /lab')
    root.mkdir(parents=True, exist_ok=False)
    for d in ('bin', 'sbin', 'usr/bin', 'usr/sbin', 'proc', 'sys', 'dev', 'run', 'tmp', 'etc'):
        (root / d).mkdir(parents=True, exist_ok=True)

    copied = set()
    def binary(src, target=None):
        src = Path(src)
        target = target or src
        dst = root / str(target).lstrip('/')
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst, follow_symlinks=True)
        if src in copied:
            return
        copied.add(src)
        info = subprocess.run(['ldd', str(src)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in info.stdout.splitlines():
            match = re.search(r'(?:=>\s+)?(/[^\s]+)', line)
            if match:
                lib = Path(match[1])
                libdst = root / str(lib).lstrip('/')
                libdst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(lib, libdst, follow_symlinks=True)

    binary('/usr/bin/busybox', '/bin/busybox')
    for name in ('sh', 'mount', 'umount', 'mkdir', 'grep', 'tail', 'cat', 'echo', 'sleep', 'sync', 'poweroff', 'uname', 'dmesg', 'timeout', 'ping', 'test', 'insmod', 'rmmod', 'lsmod'):
        (root / 'bin' / name).symlink_to('busybox')
    binary('/usr/sbin/ip')
    binary('/usr/sbin/nft')
    binary('/usr/sbin/modprobe')
    binary('/lab/results/nfqueue-bridge-test', '/usr/bin/nfqueue-bridge-test')
    if args.security_module_dir:
        (root / 'security-modules').mkdir()
        for name in ('dsa_filter_hook.ko', 'dsa_filter.ko'):
            shutil.copy2(args.security_module_dir / name, root / 'security-modules' / name)
    module_dir = root / 'lib/modules' / args.kernel_release
    shutil.copytree(args.modules / args.kernel_release, module_dir, symlinks=True)
    # The fixture contains the complete stripped module set: real dependencies,
    # not hard-coded aliases or dummy module providers.
    subprocess.run(['depmod', '-b', str(root), args.kernel_release], check=True)
    source = Path(__file__).with_name('nfqueue-fixture-init.sh')
    shutil.copy2(source, root / 'init')
    (root / 'init').chmod(0o755)
    archive = root.with_suffix('.cpio.gz')
    with archive.open('xb') as out:
        find = subprocess.Popen(['find', '.', '-print0'], cwd=root, stdout=subprocess.PIPE)
        cpio = subprocess.Popen(['cpio', '--null', '-o', '--format=newc', '--owner=0:0'], cwd=root,
                                stdin=find.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        find.stdout.close()
        gz = subprocess.run(['gzip', '-1'], stdin=cpio.stdout, stdout=out, check=True)
        cpio.stdout.close()
        error = cpio.communicate()[1]
        if find.wait() or cpio.returncode:
            raise RuntimeError(error.decode())
    print(archive)


if __name__ == '__main__':
    main()
