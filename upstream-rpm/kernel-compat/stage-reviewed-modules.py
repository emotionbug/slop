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
import sys

MANIFEST = Path('/usr/share/linuxoss-kernel-compat/server-profile-module-manifest-final.json')
PROFILE_CONFIG = Path('/etc/linuxoss-kernel-compat/module-profile.json')
PROFILE_SIGNATURE = Path('/etc/linuxoss-kernel-compat/module-profile.json.sig')
PROFILE_PUBLIC_KEY = Path('/usr/share/linuxoss-kernel-compat/module-profile-signing-public.pem')
SOURCE = ''
TARGET = ''
IMAGE_SHA = ''
SYMVERS_SHA = ''
RPM_RELEASE = ''
EXPECTED_IMPORTS = 0
PROFILE = []


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


def validate_target_pins(profile_data, target_release, symvers_sha):
    if profile_data.get('target_kernel_release') != target_release:
        raise RuntimeError('Signed module profile target release does not match the final manifest.')
    if profile_data.get('module_symvers_sha256') != symvers_sha:
        raise RuntimeError('Signed module profile Module.symvers hash does not match the final manifest.')


def check_crc_preflight(plan, symvers_path):
    providers = {}
    for line in Path(symvers_path).read_text().splitlines():
        fields = line.split()
        if len(fields) >= 3:
            providers[fields[1]] = int(fields[0], 16)
    imports = matched = missing = mismatched = 0
    exported = {}
    for item in plan:
        output = run(['modprobe', '--dump-modversions', item['source']])
        import_pairs = []
        for line in output.splitlines():
            fields = line.split()
            if len(fields) != 2 or not fields[0].startswith('0x'):
                continue
            imports += 1
            expected = int(fields[0], 16)
            import_pairs.append((fields[1], expected))
        import_digest = hashlib.sha256(('\n'.join('%s %08x' % p for p in sorted(import_pairs)) + '\n').encode()).hexdigest()
        if len(import_pairs) != item['profile']['import_count'] or import_digest != item['profile']['imports_sha256']:
            raise RuntimeError('A signed module import profile did not match.')
        nm_output = run(['nm', '-a', item['source']])
        crc_values = {}
        ksymtab = set()
        for line in nm_output.splitlines():
            fields = line.split()
            if len(fields) < 2:
                continue
            symbol = fields[-1]
            if symbol.startswith('__crc_'):
                try:
                    crc_values[symbol[6:]] = int(fields[0], 16) & 0xffffffff
                except ValueError:
                    continue
            elif symbol.startswith('__ksymtab_'):
                ksymtab.add(symbol[len('__ksymtab_'):])
        module_exports = {name: crc_values[name] for name in ksymtab if name in crc_values}
        export_pairs = sorted(module_exports.items())
        export_digest = hashlib.sha256(('\n'.join('%s %08x' % p for p in export_pairs) + '\n').encode()).hexdigest()
        if len(export_pairs) != item['profile']['export_count'] or export_digest != item['profile']['exports_sha256']:
            raise RuntimeError('A signed module export profile did not match.')
        exported.update(module_exports)
    for name, crc in exported.items():
        if name not in providers:
            providers[name] = crc
        elif providers[name] != crc:
            mismatched += 1
    # Count all imports again against the completed kernel + peer export set.
    matched = missing = 0
    for item in plan:
        output = run(['modprobe', '--dump-modversions', item['source']])
        for line in output.splitlines():
            fields = line.split()
            if len(fields) != 2 or not fields[0].startswith('0x'):
                continue
            actual = providers.get(fields[1])
            if actual is None:
                missing += 1
            elif actual == int(fields[0], 16):
                matched += 1
            else:
                mismatched += 1
    if imports != EXPECTED_IMPORTS or matched != imports or missing or mismatched:
        raise RuntimeError('Module CRC preflight failed: modules={} imports={} matched={} missing={} mismatch={}'.format(
            len(plan), imports, matched, missing, mismatched))
    return imports, matched


def choose_exact_source(candidates, expected):
    """Return the first existing candidate with the reviewed digest."""
    seen = set()
    for candidate in candidates:
        path = Path(candidate)
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if not path.is_file():
            continue
        if digest(path) == expected:
            return path
    raise RuntimeError('No exact reviewed module matched the root-owned profile.')


def source_candidates(module, filename, preferred):
    candidates = []
    try:
        selected = run(['modinfo', '-k', SOURCE, '-n', module])
        if selected and selected != '(builtin)':
            candidates.append(selected)
    except subprocess.CalledProcessError:
        pass
    candidates.extend((
        '/etc/linuxoss-kernel-compat/modules/' + filename,
        '/lib/modules/' + SOURCE + '/weak-updates/' + filename,
        '/lib/modules/' + SOURCE + '/extra/' + filename,
    ))
    if preferred:
        candidates.insert(0, preferred)
    return candidates


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
        raise RuntimeError('A loaded module differs from the tested local profile.')


def main():
    global SOURCE, TARGET, IMAGE_SHA, SYMVERS_SHA, RPM_RELEASE, EXPECTED_IMPORTS, PROFILE
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    cfg_stat = PROFILE_CONFIG.stat()
    if cfg_stat.st_uid != 0 or cfg_stat.st_mode & 0o077:
        raise RuntimeError('Module profile must be root-owned and mode 0600 or stricter.')
    sig_stat = PROFILE_SIGNATURE.stat()
    if sig_stat.st_uid != 0 or sig_stat.st_mode & 0o077:
        raise RuntimeError('Module profile signature must be root-owned and mode 0600 or stricter.')
    if subprocess.run(['openssl', 'dgst', '-sha256', '-verify', str(PROFILE_PUBLIC_KEY),
                       '-signature', str(PROFILE_SIGNATURE), str(PROFILE_CONFIG)],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        raise RuntimeError('Module profile signature verification failed.')
    profile_data = json.loads(PROFILE_CONFIG.read_text(encoding='utf-8'))
    SOURCE = profile_data.get('source_kernel_release', '')
    PROFILE = profile_data.get('modules', [])
    if not SOURCE or len(PROFILE) != 3:
        raise RuntimeError('Module profile must specify the tested source release and exactly three modules.')
    required = {'name', 'filename', 'sha256', 'identity_field', 'identity',
                'vermagic', 'import_count', 'imports_sha256',
                'export_count', 'exports_sha256'}
    names = [item.get('name') for item in PROFILE]
    if len(set(names)) != 3 or any(not isinstance(name, str) or not name for name in names):
        raise RuntimeError('Module profile names must be unique and non-empty.')
    if any(not required.issubset(item) for item in PROFILE):
        raise RuntimeError('Module profile entry is incomplete.')
    profile_source = SOURCE
    for item in PROFILE:
        item['preferred'] = item.get('source_hint', '')
    SOURCE = manifest['evidence']['rpm']['tested_source_kernel_release']
    if profile_source != SOURCE:
        raise RuntimeError('Signed module profile source release does not match build evidence.')
    TARGET = manifest['release']
    IMAGE_SHA = manifest['provenance']['bzimage_sha256']
    SYMVERS_SHA = manifest['provenance']['module_symvers_sha256']
    validate_target_pins(profile_data, TARGET, SYMVERS_SHA)
    RPM_RELEASE = manifest['evidence']['rpm']['package_release'] + '.' + TARGET.rsplit('.', 1)[-1]
    EXPECTED_IMPORTS = manifest['evidence']['external_module_abi']['final_kernel']['imports']
    if profile_data.get('expected_imports') != EXPECTED_IMPORTS:
        raise RuntimeError('Signed module profile import total does not match build evidence.')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('check', 'apply'), nargs='?', default='check')
    args = p.parse_args()
    if os.geteuid() != 0:
        raise RuntimeError('Run with sudo /usr/libexec/platform-python.')
    if os.uname().release not in (SOURCE, TARGET):
        raise RuntimeError('Running kernel is outside the signed profile source/target pair.')
    if args.mode == 'apply' and os.uname().release != SOURCE:
        raise RuntimeError('Module staging is only permitted from the validated source kernel.')
    with open('/run/linuxoss-install.lock', 'a') as lock:
        if os.environ.get('LINUXOSS_LOCK_HELD') != '1':
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require_hash('/boot/vmlinuz-' + TARGET, IMAGE_SHA)
        symvers = Path('/usr/src/kernels') / TARGET / 'Module.symvers'
        require_hash(symvers, SYMVERS_SHA)
        for package in ('kernel-linuxoss-el8-compat', 'kernel-linuxoss-el8-compat-devel'):
            run(['rpm', '-V', package + '-' + RPM_RELEASE])
        before = run(['grubby', '--default-kernel'])
        destination = Path('/lib/modules') / TARGET / 'extra/linuxoss-reviewed'
        if destination.is_symlink():
            raise RuntimeError('Destination directory must not be a symlink')
        actual_root = (Path('/lib/modules') / TARGET).resolve()
        if actual_root not in destination.resolve().parents:
            raise RuntimeError('Destination escaped the target kernel tree')
        plan = []
        for item in PROFILE:
            name = item['name']
            filename = item['filename']
            expected = item['sha256']
            check_live_identity(Path('/sys/module'), name, item['identity_field'], item['identity'])
            source = choose_exact_source(
                source_candidates(name, filename, item['preferred']), expected)
            if (run(['modinfo', '-F', 'name', source]) != name or
                    run(['modinfo', '-F', 'vermagic', source]) != item['vermagic'] or
                    run(['modinfo', '-F', item['identity_field'], source]) != item['identity']):
                raise RuntimeError('A reviewed module identity mismatch was detected.')
            target = destination / filename
            if target.is_symlink():
                raise RuntimeError('Destination module must not be a symlink')
            if args.mode == 'check' and not target.is_file():
                raise RuntimeError('Reviewed module has not been staged into the target kernel tree.')
            if target.exists():
                require_hash(target, expected)
            plan.append({'module':name,'source':str(source),'destination':str(target),'sha256':expected,'profile':item})
        imports, matched = check_crc_preflight(plan, symvers)
        print('mode={} target_kernel={} reviewed_modules={} imports={} matched={} missing=0 mismatch=0'.format(
            args.mode, TARGET, len(plan), imports, matched))
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
    if len(sys.argv) > 1 and sys.argv[1] in ('--local-running', '--local-profile-check'):
        helper = Path(__file__).with_name('stage-local-running-modules.py')
        os.execv('/usr/libexec/platform-python', ['/usr/libexec/platform-python', str(helper)] + sys.argv[1:])
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError):
        raise SystemExit('ERROR: reviewed module preflight or staging failed; inspect root-only log.')
