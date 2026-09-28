import importlib.util
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('local_stage', HERE / 'stage-local-running-modules.py')
local = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(local)


class LocalRunningModuleTests(unittest.TestCase):
    def test_names_are_generic_and_normalized_distinct(self):
        self.assertEqual(local.names3(['alpha_mod', 'beta-mod', 'gamma']),
                         ['alpha_mod', 'beta_mod', 'gamma'])
        with self.assertRaises(RuntimeError):
            local.names3(['alpha-mod', 'alpha_mod', 'gamma'])
        with self.assertRaises(RuntimeError):
            local.names3(['../alpha', 'beta', 'gamma'])

    def test_loaded_module_list_and_live_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            modules = root / 'modules'
            modules.write_text('alpha_mod 1 0 - Live 0\nbeta 1 0 - Live 0\n')
            self.assertEqual(local.loaded_modules(modules), {'alpha_mod', 'beta'})
            sysroot = root / 'sys' / 'alpha_mod'
            sysroot.mkdir(parents=True)
            (sysroot / 'srcversion').write_text('SRC-1')
            local.check_live_identity(root / 'sys', 'alpha_mod', {'srcversion': 'SRC-1'})
            with self.assertRaises(RuntimeError):
                local.check_live_identity(root / 'sys', 'alpha_mod', {'srcversion': 'SRC-2'})

    def test_loaded_kabi_module_may_have_older_vermagic_release(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'alpha.ko'
            source.write_bytes(b'fixture')
            metadata = {'name': 'alpha', 'vermagic':
                        '4.18.0-553.123.1.el8_10.x86_64 SMP mod_unload modversions',
                        'srcversion': 'SRC-1'}
            with mock.patch.object(local, 'loaded_modules', return_value={'alpha'}), \
                    mock.patch.object(local, 'source_candidates', return_value=[str(source)]), \
                    mock.patch.object(local, 'run', return_value='\n'.join(
                        '{}: {}'.format(k, v) for k, v in metadata.items())), \
                    mock.patch.object(local, 'check_live_identity'):
                plan = local.inspect_running_module('alpha', '4.18.0-553.166.1.el8_10.x86_64')
                self.assertEqual(plan['vermagic'], metadata['vermagic'])
                self.assertEqual(plan['srcversion'], 'SRC-1')

    def test_crc_contract_includes_target_and_peer_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            symvers = Path(temp) / 'Module.symvers'
            symvers.write_text('0x00000001 kernel_sym vmlinux EXPORT_SYMBOL\n'
                               '0x00000002 peer_sym peer EXPORT_SYMBOL\n')
            plan = [
                {'module': 'alpha', 'source': 'unused',
                 'imports': [('kernel_sym', 1), ('peer_sym', 2)],
                 'exports': {'peer_sym': 2}},
                {'module': 'beta', 'source': 'unused',
                 'imports': [('kernel_sym', 1)], 'exports': {}},
            ]
            self.assertEqual(local.check_crc_compatibility(plan, symvers, 3), (3, 3))
            plan[1]['imports'] = [('kernel_sym', 9)]
            with self.assertRaises(RuntimeError):
                local.check_crc_compatibility(plan, symvers, 3)

    def test_copy_is_atomic_idempotent_and_refuses_different_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root / 'source.ko', root / 'extra' / 'module.ko'
            source.write_bytes(b'fixture module bytes')
            sha = local.digest(source)
            self.assertTrue(local.atomic_copy(source, target, sha))
            self.assertEqual(local.digest(source), sha)
            self.assertFalse(local.atomic_copy(source, target, sha))
            target.write_bytes(b'other module')
            with self.assertRaises(RuntimeError):
                local.atomic_copy(source, target, sha)

    def test_existing_target_contract_is_pinned_to_328_imports(self):
        import json
        manifest = json.loads((HERE / 'server-profile-module-manifest-final.json').read_text())
        self.assertEqual(manifest['evidence']['external_module_abi']['final_kernel']['imports'], 328)
        self.assertEqual(manifest['release'], '4.18.0-553.168.1.linuxoss2.el8_10.x86_64')

    def test_helper_dispatch_modes_keep_three_names_and_separate_profile_check(self):
        original = local.execute_local
        calls = []
        local.execute_local = lambda *args, **kwargs: calls.append((args, kwargs))
        try:
            sys.argv = ['stage-local-running-modules.py', '--local-running', 'apply',
                        'alpha', 'beta', 'gamma']
            local.main()
            self.assertEqual(calls[-1][0], ('apply', ['alpha', 'beta', 'gamma']))
            sys.argv = ['stage-local-running-modules.py', '--local-profile-check']
            local.main()
            self.assertEqual(calls[-1], (('check',), {'state_only': True}))
        finally:
            local.execute_local = original


if __name__ == '__main__':
    unittest.main()
