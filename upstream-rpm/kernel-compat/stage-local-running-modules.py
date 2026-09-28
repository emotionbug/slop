#!/usr/libexec/platform-python
"""Copy three already-loaded local modules to the pinned parallel kernel.

The module names are supplied by the operator. No module-specific names,
hashes, product paths, or signing material are embedded in this program.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

MANIFEST = Path('/usr/share/linuxoss-kernel-compat/server-profile-module-manifest-final.json')
STATE = Path('/var/lib/linuxoss-kernel-compat/local-module-profile.json')
LOCK = '/run/linuxoss-install.lock'
MODULE_ROOT = Path('/lib/modules')


def run(args):
    return subprocess.check_output([str(x) for x in args], universal_newlines=True,
                                   stderr=subprocess.STDOUT).strip()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def normalized(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', name):
        raise RuntimeError('Module names must be simple identifiers.')
    return name.replace('-', '_')


def names3(values):
    if len(values) != 3:
        raise RuntimeError('Exactly three module names are required.')
    normalized_names = [normalized(v) for v in values]
    if len(set(normalized_names)) != 3:
        raise RuntimeError('The three module names must be unique.')
    return normalized_names


def parse_fields(output):
    fields = {}
    for line in output.splitlines():
        key, sep, value = line.partition(':')
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def loaded_modules(proc_modules='/proc/modules'):
    return {normalized(line.split()[0]) for line in Path(proc_modules).read_text().splitlines()
            if line.split()}


def check_live_identity(sysroot, module, metadata):
    base = Path(sysroot) / module
    matches = 0
    for field in ('srcversion', 'version'):
        expected = metadata.get(field, '').strip()
        loaded = base / field
        if expected and loaded.is_file():
            if loaded.read_text().strip() != expected:
                raise RuntimeError('Loaded module identity differs from its modinfo file.')
            matches += 1
    if not matches:
        raise RuntimeError('Cannot prove the loaded module identity from modinfo metadata.')


def source_candidates(module, running, roots=None):
    candidates = []
    try:
        selected = run(['modinfo', '-k', running, '-n', module])
        if selected and selected != '(builtin)':
            candidates.append(selected)
    except (subprocess.CalledProcessError, OSError):
        pass
    roots = roots or [MODULE_ROOT / running, Path('/usr/lib/modules') / running,
                      Path('/opt'), Path('/usr/lib'), Path('/var/opt')]
    filenames = {module + '.ko', module.replace('_', '-') + '.ko'}
    filenames = {n + suffix for n in filenames for suffix in ('', '.gz', '.xz', '.zst')}
    count = 0
    for root in roots:
        if not root.is_dir():
            continue
        for directory, dirs, files in os.walk(str(root), followlinks=False):
            depth = len(Path(directory).relative_to(root).parts)
            if depth >= 8:
                dirs[:] = []
            for filename in files:
                count += 1
                if count > 100000:
                    raise RuntimeError('Module search exceeded the safe file limit.')
                if filename in filenames:
                    candidates.append(str(Path(directory) / filename))
    seen = set()
    return [p for p in candidates if not (str(Path(p)) in seen or seen.add(str(Path(p))))]


def inspect_running_module(module, running, proc_modules='/proc/modules', sysroot='/sys/module', roots=None):
    if module not in loaded_modules(proc_modules):
        raise RuntimeError('Every requested module must be loaded in the running kernel.')
    last_error = None
    for candidate in source_candidates(module, running, roots):
        path = Path(candidate)
        try:
            if not path.is_file():
                continue
            metadata = parse_fields(run(['modinfo', str(path)]))
            if normalized(metadata.get('name', '')) != module:
                continue
            vermagic = metadata.get('vermagic', '').split()
            # RHEL kABI-compatible third-party modules may legitimately carry
            # an older release token. Live identity plus every import/export
            # CRC is the compatibility gate; require matching architecture and
            # modversions metadata rather than an exact release-token match.
            if not any('x86_64' in token for token in vermagic) or 'modversions' not in vermagic:
                continue
            check_live_identity(sysroot, module, metadata)
            return {'name': module, 'source': str(path.resolve()), 'sha256': digest(path),
                    'vermagic': metadata.get('vermagic', ''), 'srcversion': metadata.get('srcversion', ''),
                    'version': metadata.get('version', ''),
                    'depends': metadata.get('depends', '')}
        except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
            last_error = error
    raise RuntimeError('No modinfo file matched a loaded module and its live identity.' +
                       ((' ' + str(last_error)) if last_error else ''))


def module_imports(path):
    output = run(['modprobe', '--dump-modversions', str(path)])
    pairs = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0].startswith('0x'):
            pairs.append((fields[1], int(fields[0], 16) & 0xffffffff))
    if not pairs:
        raise RuntimeError('Cannot read CONFIG_MODVERSIONS imports from a requested module.')
    return pairs


def module_exports(path):
    output = run(['nm', '-a', str(path)])
    crc_values, exported_names = {}, set()
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 2:
            continue
        symbol = fields[-1]
        if symbol.startswith('__crc_'):
            try:
                crc_values[symbol[6:]] = int(fields[0], 16) & 0xffffffff
            except ValueError:
                pass
        elif symbol.startswith('__ksymtab_'):
            exported_names.add(symbol[len('__ksymtab_'):])
    exports = {name: crc_values[name] for name in exported_names if name in crc_values}
    # Some vendor modules expose ksymtab metadata without a corresponding
    # __crc_* record. Only versioned exports can satisfy a versioned import;
    # any required unversioned peer export is therefore rejected later as a
    # missing provider by the full import check.
    return exports


def symvers_providers(path):
    result = {}
    for number, line in enumerate(Path(path).read_text().splitlines(), 1):
        fields = line.split()
        if len(fields) < 3:
            raise RuntimeError('Malformed target Module.symvers row {}.'.format(number))
        try:
            crc = int(fields[0], 16) & 0xffffffff
        except ValueError:
            raise RuntimeError('Malformed target Module.symvers CRC.')
        if fields[1] in result and result[fields[1]] != crc:
            raise RuntimeError('Target Module.symvers contains conflicting providers.')
        result[fields[1]] = crc
    return result


def check_crc_compatibility(plan, symvers_path, expected_imports, run_fn=run):
    providers = symvers_providers(symvers_path)
    exports = {}
    imports_by_module = {}
    for item in plan:
        imports = item.get('imports')
        if imports is None:
            imports = module_imports(item['source'])
        module_exports_map = item.get('exports')
        if module_exports_map is None:
            module_exports_map = module_exports(item['source'])
        imports_by_module[item['module']] = imports
        for symbol, crc in module_exports_map.items():
            if symbol in providers and providers[symbol] != crc:
                raise RuntimeError('Peer export CRC conflicts with the target kernel.')
            if symbol in exports and exports[symbol] != crc:
                raise RuntimeError('Peer modules export conflicting CRCs.')
            exports[symbol] = crc
    providers.update(exports)
    total = matched = missing = mismatched = 0
    for imports in imports_by_module.values():
        for symbol, expected in imports:
            total += 1
            actual = providers.get(symbol)
            if actual is None:
                missing += 1
            elif actual != expected:
                mismatched += 1
            else:
                matched += 1
    if total != expected_imports or matched != total or missing or mismatched:
        raise RuntimeError('Target ABI check failed: imports={} matched={} missing={} mismatch={}'.format(
            total, matched, missing, mismatched))
    return total, matched


def target_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    target = manifest['release']
    provenance = manifest['provenance']
    evidence = manifest['evidence']
    image = Path('/boot/vmlinuz-' + target)
    symvers = Path('/usr/src/kernels') / target / 'Module.symvers'
    if digest(image) != provenance['bzimage_sha256']:
        raise RuntimeError('Target boot image does not match the pinned manifest.')
    if digest(symvers) != provenance['module_symvers_sha256']:
        raise RuntimeError('Target Module.symvers does not match the pinned manifest.')
    rpm_release = evidence['rpm']['package_release'] + '.' + target.rsplit('.', 1)[-1]
    for package in evidence['rpm']['packages']:
        expected_nevra = package['nevra']
        actual = run(['rpm', '-q', '--qf', '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}',
                      expected_nevra])
        if actual != expected_nevra:
            raise RuntimeError('Target RPM identity does not match the pinned manifest.')
        if run(['rpm', '-V', expected_nevra]):
            raise RuntimeError('Installed target RPM files differ from the pinned package.')
    expected_imports = evidence['external_module_abi']['final_kernel']['imports']
    if expected_imports != 328:
        raise RuntimeError('Pinned final-kernel import-count contract is not the expected manifest profile.')
    return manifest, target, symvers, expected_imports, rpm_release


def atomic_copy(source, target, expected_hash):
    if digest(source) != expected_hash:
        raise RuntimeError('Source module changed during preflight.')
    if target.is_symlink():
        raise RuntimeError('Target module destination is a symlink.')
    if target.exists():
        if digest(target) != expected_hash:
            raise RuntimeError('Existing target module differs; refusing overwrite.')
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix='.local-kmod-', dir=str(target.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, 'wb') as out, Path(source).open('rb') as inp:
            for block in iter(lambda: inp.read(1024 * 1024), b''):
                out.write(block)
            out.flush()
            os.fsync(out.fileno())
        if digest(temp) != expected_hash:
            raise RuntimeError('Atomic copy hash mismatch.')
        os.chmod(temp, 0o644)
        os.link(str(temp), str(target))
        dfd = os.open(str(target.parent), os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
    return True


def save_profile(profile):
    STATE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(STATE.parent, 0o700)
    fd, temp_name = tempfile.mkstemp(prefix='.local-profile-', dir=str(STATE.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(profile, out, indent=2, sort_keys=True)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temp, 0o600)
        os.replace(str(temp), str(STATE))
        dfd = os.open(str(STATE.parent), os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def verify_profile_loaded(profile, target, symvers, expected_imports):
    running = os.uname().release
    if running not in (profile['source_kernel_release'], target):
        raise RuntimeError('Running kernel is outside the saved local migration profile.')
    loaded = loaded_modules()
    plan = []
    base = MODULE_ROOT / target / 'extra/linuxoss-local-migration'
    for item in profile['modules']:
        name = item['name']
        if name not in loaded:
            raise RuntimeError('A profile module is not loaded in the current kernel.')
        path = Path(item['destination'])
        if not path.is_file() or path.is_symlink() or digest(path) != item['sha256']:
            raise RuntimeError('A staged module is absent or differs from the saved local profile.')
        meta = parse_fields(run(['modinfo', str(path)]))
        if normalized(meta.get('name', '')) != name:
            raise RuntimeError('Staged module name differs from the saved local profile.')
        check_live_identity(Path('/sys/module'), name, meta)
        selected = Path(run(['modinfo', '-k', target, '-n', name]))
        if selected.resolve() != path.resolve():
            raise RuntimeError('Target module index does not select the local migration copy.')
        plan.append({'module': name, 'source': str(path)})
    return check_crc_compatibility(plan, symvers, expected_imports)


def execute_local(mode, names=None, state_only=False):
    if os.geteuid() != 0:
        raise RuntimeError('Run with sudo /usr/libexec/platform-python.')
    manifest, target, symvers, expected_imports, rpm_release = target_manifest()
    with open(LOCK, 'a') as lock:
        if os.environ.get('LINUXOSS_LOCK_HELD') != '1':
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = run(['grubby', '--default-kernel'])
        if state_only:
            info = STATE.stat()
            if info.st_uid != 0 or info.st_mode & 0o077:
                raise RuntimeError('Saved local profile must be root-owned and mode 0600 or stricter.')
            profile = json.loads(STATE.read_text(encoding='utf-8'))
            if (profile.get('target_kernel_release') != target or
                    profile.get('target_image_sha256') != manifest['provenance']['bzimage_sha256'] or
                    profile.get('target_symvers_sha256') != manifest['provenance']['module_symvers_sha256'] or
                    profile.get('manifest_sha256') != digest(MANIFEST)):
                raise RuntimeError('Saved local profile does not match target manifest pins.')
            total, matched = verify_profile_loaded(profile, target, symvers, expected_imports)
            print('local_profile=PASS modules=3 imports={} matched={}'.format(total, matched))
            return
        names = names3(names or [])
        running = os.uname().release
        if running != manifest['evidence']['rpm']['tested_source_kernel_release']:
            raise RuntimeError('Run local migration from the manifest-pinned source kernel.')
        plan = [inspect_running_module(name, running) for name in names]
        destination = MODULE_ROOT / target / 'extra/linuxoss-local-migration'
        if destination.is_symlink() or MODULE_ROOT.joinpath(target).resolve() not in destination.resolve().parents:
            raise RuntimeError('Local migration destination escaped the target module tree.')
        for item in plan:
            filename = Path(item['source']).name
            if not re.fullmatch(r'[A-Za-z0-9_.+-]+\.ko(?:\.(?:gz|xz|zst))?', filename):
                raise RuntimeError('Unsupported module filename; no file was changed.')
            target_file = destination / filename
            if target_file.is_symlink():
                raise RuntimeError('Target module destination is a symlink.')
            item['destination'] = str(target_file)
            item['module'] = item.pop('name')
        total, matched = check_crc_compatibility(plan, symvers, expected_imports)
        print('mode={} target={} modules=3 imports={} matched={} root={} rpm_release={}'.format(
            mode, target, total, matched, destination, rpm_release))
        for item in plan:
            if Path(item['destination']).exists() and digest(item['destination']) != item['sha256']:
                raise RuntimeError('Existing target path contains different bytes; refusing overwrite.')
        if mode == 'check':
            if run(['grubby', '--default-kernel']) != before:
                raise RuntimeError('Boot default changed during read-only check.')
            print('CHECK_COMPLETED_NO_CHANGES')
            return
        for item in plan:
            atomic_copy(item['source'], Path(item['destination']), item['sha256'])
        run(['depmod', '-a', target])
        for item in plan:
            selected = Path(run(['modinfo', '-k', target, '-n', item['module']]))
            if selected.resolve() != Path(item['destination']).resolve():
                raise RuntimeError('depmod selected a different target module.')
            if digest(selected) != item['sha256']:
                raise RuntimeError('depmod-selected module hash differs from the copied source.')
        profile = {'schema_version': 1, 'profile_type': 'local-running-modules',
                   'source_kernel_release': running, 'target_kernel_release': target,
                   'target_image_sha256': manifest['provenance']['bzimage_sha256'],
                   'target_symvers_sha256': manifest['provenance']['module_symvers_sha256'],
                   'manifest_sha256': digest(MANIFEST), 'expected_imports': expected_imports,
                   'imports_matched': matched, 'modules': [
                       {'name': x['module'], 'source_sha256': x['sha256'],
                        'destination': x['destination'], 'sha256': x['sha256'],
                        'srcversion': x['srcversion'], 'version': x['version'],
                        'vermagic': x['vermagic']} for x in plan]}
        save_profile(profile)
        if run(['grubby', '--default-kernel']) != before:
            raise RuntimeError('Boot default changed unexpectedly; inspect before proceeding.')
        print('LOCAL_MODULES_STAGED_NO_LOAD_NO_BOOT_CHANGE')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('check', 'apply'), nargs='?', default='check')
    parser.add_argument('modules', nargs='*')
    parser.add_argument('--local-running', action='store_true')
    parser.add_argument('--local-profile-check', action='store_true')
    args = parser.parse_args()
    if args.local_profile_check:
        if args.modules:
            raise RuntimeError('--local-profile-check takes no module names.')
        return execute_local('check', state_only=True)
    if args.local_running:
        if len(args.modules) != 3:
            raise RuntimeError('--local-running requires exactly three module names.')
        return execute_local(args.mode, args.modules)
    raise RuntimeError('Use --local-running or --local-profile-check with this helper.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError, KeyError, ValueError) as error:
        raise SystemExit('ERROR: local module preflight or staging failed: {}'.format(error))
