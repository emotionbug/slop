"""ELF fixtures for the read-only audit. Run with Python >= 3.6, gcc and readelf."""
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    'symbol_audit', str(pathlib.Path(__file__).resolve().parents[1] / 'check-removed-symbol-users.py'))
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


@unittest.skipUnless(shutil.which('gcc') and shutil.which('readelf'), 'gcc/readelf required')
class RemovedSymbolAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='symbol-audit-test-')
        self.root = pathlib.Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def audit(self, paths, only=True):
        args = ['audit'] + (['--only-roots'] if only else []) + [str(p) for p in paths]
        output = io.StringIO()
        with mock.patch.object(sys, 'argv', args), contextlib.redirect_stdout(output):
            code = AUDIT.main()
        return code, json.loads(output.getvalue())

    def make_consumer(self):
        provider = self.root / 'provider.c'
        provider.write_text('const char *jpeg_std_message_table[]={"fixture"};\n'
                            'int ZSTD_getSequences(void){return 0;}\n')
        consumer = self.root / 'consumer.c'
        consumer.write_text('extern const char *jpeg_std_message_table[];\n'
                            'extern int ZSTD_getSequences(void);\n'
                            'int main(void){return ZSTD_getSequences()+'
                            '(jpeg_std_message_table[0]==0);}\n')
        library = self.root / 'libfixture.so'
        executable = self.root / 'consumer'
        subprocess.check_call(['gcc', '-fPIC', '-shared', str(provider), '-o', str(library)])
        subprocess.check_call(['gcc', '-fno-pie', '-no-pie', str(consumer), str(library),
                               '-o', str(executable)])
        relocations = subprocess.check_output(['readelf', '--relocs', '--wide', str(executable)])
        self.assertIn(b'R_X86_64_COPY', relocations)
        return executable

    def test_undefined_function_and_copy_relocation_are_both_found(self):
        executable = self.make_consumer()
        os.link(str(executable), str(self.root / 'hardlink'))
        code, result = self.audit([self.root])
        self.assertEqual(code, 1)
        self.assertFalse(result['errors'])
        self.assertEqual(result['elf_files_scanned'], 2)  # provider + deduplicated consumer
        self.assertEqual(len(result['direct_import_matches']), 1)
        self.assertEqual(result['direct_import_matches'][0]['symbols'], sorted(AUDIT.SYMBOLS))
        self.assertEqual(set(result['direct_import_matches'][0]['aliases']),
                         {str(executable), str(self.root / 'hardlink')})

    def test_missing_symlink_is_not_silently_ignored(self):
        path = self.root / 'dangling'
        path.symlink_to('absent-target')
        code, result = self.audit([path])
        self.assertEqual(code, 2)
        self.assertFalse(result['coverage_complete_for_declared_roots'])
        self.assertEqual(result['errors'][0]['kind'], 'broken_symlink')
        self.assertEqual(result['errors'][0]['link_target'], 'absent-target')
        self.assertTrue(path.is_symlink())  # audit did not repair/delete it

    def test_missing_regular_path_is_distinct(self):
        code, result = self.audit([self.root / 'missing'])
        self.assertEqual(code, 2)
        self.assertEqual(result['errors'][0]['kind'], 'missing_path')

    def test_outside_directory_link_requires_its_target_as_an_extra_root(self):
        inside, outside = self.root / 'inside', self.root / 'outside'
        inside.mkdir()
        outside.mkdir()
        (inside / 'linked').symlink_to(outside, target_is_directory=True)
        (outside / 'cycle').symlink_to(inside, target_is_directory=True)
        code, result = self.audit([inside])
        self.assertEqual(code, 2)
        self.assertEqual(len(result['directory_symlinks_outside_roots']), 1)
        code, result = self.audit([inside, outside])
        self.assertEqual(code, 0)
        self.assertFalse(result['directory_symlinks_outside_roots'])
        self.assertTrue(result['coverage_complete_for_declared_roots'])

    def test_positional_paths_extend_defaults(self):
        default = self.root / 'default'
        extra = self.root / 'extra'
        default.mkdir()
        extra.mkdir()
        self.assertIn('/usr/lib', AUDIT.DEFAULT_ROOTS)
        with mock.patch.object(AUDIT, 'DEFAULT_ROOTS', [str(default)]):
            code, result = self.audit([extra], only=False)
        self.assertEqual(code, 0)
        self.assertEqual(result['roots'], [str(default), str(extra)])

    def test_benign_elf_has_no_target_imports(self):
        source = self.root / 'benign.c'
        source.write_text('int main(void){return 0;}\n')
        binary = self.root / 'benign'
        subprocess.check_call(['gcc', str(source), '-o', str(binary)])
        code, result = self.audit([binary])
        self.assertEqual(code, 0)
        self.assertEqual(result['elf_files_scanned'], 1)
        self.assertFalse(result['direct_import_matches'])

    def test_missing_symlink_inside_a_tree_is_reported(self):
        (self.root / 'dangling').symlink_to('missing')
        code, result = self.audit([self.root])
        self.assertEqual(code, 2)
        self.assertEqual(result['errors'][0]['kind'], 'broken_symlink')

    def test_special_files_are_not_opened(self):
        os.mkfifo(str(self.root / 'pipe'))
        code, result = self.audit([self.root])
        self.assertEqual(code, 0)
        self.assertEqual(result['elf_files_scanned'], 0)

    def test_added_symbol_file_finds_real_undefined_import(self):
        source = self.root / 'puts.c'
        source.write_text('#include <stdio.h>\nint main(void){return puts("fixture")<0;}\n')
        binary = self.root / 'puts-test'
        subprocess.check_call(['gcc', str(source), '-o', str(binary)])
        symbols = self.root / 'symbols.json'
        symbols.write_text(json.dumps({'libraries':[{'scan_symbols':['puts']}]}))
        args = ['audit','--only-roots','--symbols-file',str(symbols),str(binary)]
        output = io.StringIO()
        with mock.patch.object(sys,'argv',args), contextlib.redirect_stdout(output):
            code = AUDIT.main()
        result = json.loads(output.getvalue())
        self.assertEqual(code,1)
        self.assertEqual(result['direct_import_matches'][0]['symbols'],['puts'])
        self.assertEqual(result['audit_version'],3)


if __name__ == '__main__':
    unittest.main()
