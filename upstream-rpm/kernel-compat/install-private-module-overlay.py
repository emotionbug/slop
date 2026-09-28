#!/usr/bin/env python3
"""Install a separately delivered, signed three-module profile overlay."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', required=True, type=Path)
    p.add_argument('--public-key', required=True, type=Path)
    p.add_argument('--dest', default=Path('/etc/linuxoss-kernel-compat'), type=Path)
    args = p.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Run as root.')
    with tarfile.open(args.archive, 'r:*') as tf:
        members = tf.getmembers()
        by_name = {m.name: m for m in members}
        required_base = {'module-profile.json', 'module-profile.json.sig'}
        if len(members) != 5 or len(by_name) != 5 or not required_base.issubset(by_name):
            raise RuntimeError('Private overlay must contain exactly five regular files.')
        if any(not m.isfile() for m in members):
            raise RuntimeError('Links and non-regular overlay entries are forbidden.')
        for m in members:
            path = PurePosixPath(m.name)
            if path.is_absolute() or '..' in path.parts:
                raise RuntimeError('Unsafe overlay path.')
        profile_member = tf.extractfile(by_name['module-profile.json'])
        sig_member = tf.extractfile(by_name['module-profile.json.sig'])
        if profile_member is None or sig_member is None:
            raise RuntimeError('Overlay profile is incomplete.')
        profile_bytes = profile_member.read()
        signature_bytes = sig_member.read()
        profile = json.loads(profile_bytes)
        modules = profile.get('modules', [])
        if len(modules) != 3 or len({m.get('name') for m in modules}) != 3:
            raise RuntimeError('Signed profile must specify exactly three unique modules.')
        expected_paths = {'module-profile.json', 'module-profile.json.sig'}
        for item in modules:
            filename = item.get('filename', '')
            if not filename or '/' in filename or '\\' in filename or filename in ('.', '..'):
                raise RuntimeError('Invalid signed module filename.')
            expected_paths.add('modules/' + filename)
        if set(by_name) != expected_paths:
            raise RuntimeError('Overlay contents do not match the signed profile.')
        with tempfile.TemporaryDirectory(prefix='linuxoss-profile-') as tmp:
            temp = Path(tmp)
            profile_path = temp / 'module-profile.json'
            sig_path = temp / 'module-profile.json.sig'
            profile_path.write_bytes(profile_bytes)
            sig_path.write_bytes(signature_bytes)
            verify = subprocess.run(['openssl', 'dgst', '-sha256', '-verify', str(args.public_key),
                                     '-signature', str(sig_path), str(profile_path)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if verify.returncode:
                raise RuntimeError('Overlay profile signature verification failed.')
            staged = {}
            for item in modules:
                member = by_name['modules/' + item['filename']]
                if member.size > 256 * 1024 * 1024:
                    raise RuntimeError('Overlay module exceeds the size limit.')
                source = tf.extractfile(member)
                if source is None:
                    raise RuntimeError('Overlay module payload is missing.')
                path = temp / item['filename']
                with source, path.open('wb') as output:
                    for block in iter(lambda: source.read(1024 * 1024), b''):
                        output.write(block)
                if sha(path) != item.get('sha256'):
                    raise RuntimeError('Overlay module hash does not match its signed profile.')
                staged[item['filename']] = path
            args.dest.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(args.dest, 0o700)
            module_dir = args.dest / 'modules'
            module_dir.mkdir(mode=0o700, exist_ok=True)
            os.chmod(module_dir, 0o700)
            targets = [(profile_path, args.dest / 'module-profile.json', 0o600),
                       (sig_path, args.dest / 'module-profile.json.sig', 0o600)]
            targets.extend((src, module_dir / name, 0o600) for name, src in staged.items())
            for _, target, _ in targets:
                if target.exists() or target.is_symlink():
                    raise RuntimeError('Overlay destination already contains profile data.')
            for source, target, mode in targets:
                with source.open('rb') as src, target.open('xb') as dst:
                    for block in iter(lambda: src.read(1024 * 1024), b''):
                        dst.write(block)
                os.chmod(target, mode)
    print('signed_overlay=PASS modules=3 files=5 private_payloads_extracted=3')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, tarfile.TarError):
        raise SystemExit('ERROR: signed private module overlay verification/installation failed.')
