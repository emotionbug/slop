#!/usr/bin/env python3
"""Generic tests for signed overlay validation and the runtime CRC gate."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


HERE = Path(__file__).resolve().parent
OVERLAY_INSTALLER = HERE / 'install-private-module-overlay.py'
STAGE_SCRIPT = HERE / 'stage-reviewed-modules.py'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_digest(pairs):
    return hashlib.sha256(('\n'.join('%s %08x' % item for item in sorted(pairs)) + '\n').encode()).hexdigest()


def invoke_overlay(archive, public_key, dest):
    return subprocess.run([sys.executable, str(OVERLAY_INSTALLER), '--archive', str(archive),
                           '--public-key', str(public_key), '--dest', str(dest)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)


def create_overlay(root, private_key, module_contents, bad_signature=False):
    module_names = ['sample_a.ko', 'sample_b.ko', 'sample_c.ko']
    modules = []
    for i, name in enumerate(module_names):
        data = module_contents[i]
        modules.append({'name': 'sample_' + chr(ord('a') + i), 'filename': name, 'sha256': sha(data)})
    profile = {'schema_version': 1, 'source_kernel_release': 'test-source',
               'expected_imports': 0, 'modules': modules}
    profile_path = root / 'module-profile.json'
    profile_path.write_text(json.dumps(profile, sort_keys=True, indent=2) + '\n')
    sig_path = root / 'module-profile.json.sig'
    subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(private_key), '-out', str(sig_path),
                    str(profile_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if bad_signature:
        sig_path.write_bytes(b'bad signature')
    modules_dir = root / 'modules'
    modules_dir.mkdir(exist_ok=True)
    for name, data in zip(module_names, module_contents):
        (modules_dir / name).write_bytes(data)
    archive = root / 'overlay.tar'
    with tarfile.open(archive, 'w') as tf:
        for path in [profile_path, sig_path, *(modules_dir / n for n in module_names)]:
            tf.add(path, arcname=path.relative_to(root).as_posix())
    return archive, profile_path, sig_path, module_names


def test_overlay(root):
    key = root / 'private.pem'
    pub = root / 'public.pem'
    subprocess.run(['openssl', 'genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:2048',
                    '-out', str(key)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['openssl', 'pkey', '-in', str(key), '-pubout', '-out', str(pub)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    contents = [b'module-a', b'module-b', b'module-c']
    valid, profile, signature, names = create_overlay(root / 'good', key, contents)
    out = root / 'dest-good'
    result = invoke_overlay(valid, pub, out)
    assert result.returncode == 0 and 'modules=3 files=5' in result.stdout
    assert all((out / 'modules' / name).is_file() for name in names)
    bad, _, _, _ = create_overlay(root / 'bad-signature', key, contents, bad_signature=True)
    result = invoke_overlay(bad, pub, root / 'dest-bad-signature')
    assert result.returncode != 0 and not (root / 'dest-bad-signature' / 'module-profile.json').exists()
    altered, profile, signature, names = create_overlay(root / 'altered', key, contents)
    with tarfile.open(altered, 'w') as tf:
        tf.add(profile, arcname='module-profile.json')
        tf.add(signature, arcname='module-profile.json.sig')
        for i, name in enumerate(names):
            data = contents[i] + (b'-tampered' if i == 1 else b'')
            temp = root / ('payload-' + str(i))
            temp.write_bytes(data)
            tf.add(temp, arcname='modules/' + name)
    result = invoke_overlay(altered, pub, root / 'dest-altered')
    assert result.returncode != 0 and not (root / 'dest-altered' / 'module-profile.json').exists()


def test_crc_gate(root):
    spec = importlib.util.spec_from_file_location('stage_reviewed_modules', STAGE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    symvers = root / 'Module.symvers'
    symvers.write_text('0x11111111 symbol_a vmlinux EXPORT_SYMBOL\n')
    imports = [('symbol_a', 0x11111111), ('symbol_b', 0x22222222)]
    exports = [('symbol_b', 0x22222222)]
    item = {'source': 'test.ko', 'profile': {
        'import_count': 2, 'imports_sha256': canonical_digest(imports),
        'export_count': 1, 'exports_sha256': canonical_digest(exports)}}
    module.EXPECTED_IMPORTS = 2
    case = {'value': 'pass'}
    def fake_run(args):
        if args[0] == 'modprobe':
            crc_b = 0x33333333 if case['value'] == 'crc' else 0x22222222
            return '0x11111111 symbol_a\n0x%08x symbol_b' % crc_b
        if args[0] == 'nm':
            if case['value'] == 'missing_peer':
                return ''
            return '22222222 A __crc_symbol_b\n00000000 R __ksymtab_symbol_b'
        raise AssertionError('unexpected tool')
    module.run = fake_run
    plan = [item]
    assert module.check_crc_preflight(plan, symvers) == (2, 2)
    case['value'] = 'missing_peer'
    item['profile']['export_count'] = 0
    item['profile']['exports_sha256'] = canonical_digest([])
    try:
        module.check_crc_preflight(plan, symvers)
        raise AssertionError('missing peer export accepted')
    except RuntimeError:
        pass
    case['value'] = 'crc'
    item['profile']['export_count'] = 1
    item['profile']['exports_sha256'] = canonical_digest(exports)
    item['profile']['imports_sha256'] = canonical_digest([('symbol_a', 0x11111111), ('symbol_b', 0x33333333)])
    try:
        module.check_crc_preflight(plan, symvers)
        raise AssertionError('CRC mismatch accepted')
    except RuntimeError:
        pass
    item['profile']['imports_sha256'] = '0' * 64
    case['value'] = 'pass'
    try:
        module.check_crc_preflight(plan, symvers)
        raise AssertionError('altered module profile accepted')
    except RuntimeError:
        pass


def main():
    with tempfile.TemporaryDirectory(prefix='signed-profile-test-') as d:
        root = Path(d)
        for child in ('good', 'bad-signature', 'altered'):
            (root / child).mkdir()
        test_overlay(root)
        test_crc_gate(root)
    print('signed_overlay=PASS bad_signature=REJECT altered_module=REJECT crc_match=PASS missing_peer=REJECT crc_mismatch=REJECT altered_profile=REJECT')


if __name__ == '__main__':
    main()
