"""Run on EL8 with platform-python, gcc, rpm and readelf. No target programs run."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('diagnostic', str(
    Path(__file__).resolve().parents[1] / 'deploy' / 'diagnose-symbol-audit.py'))
DIAG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAG)


class DiagnosticsTests(unittest.TestCase):
    def test_same_name_provider_alias_and_broken_link_are_evidence_not_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            provider = root / 'provider.c'
            provider.write_text('int audit_fixture_symbol(void){return 7;}\n')
            library = root / 'libfixture.so'
            subprocess.check_call(['gcc', '-shared', '-fPIC', str(provider),
                                   '-Wl,-soname,libfixture.so', '-o', str(library)])
            source = root / 'consumer.c'
            # If inadvertently executed this consumer would fail, but diagnosis never runs it.
            source.write_text('extern int audit_fixture_symbol(void);\n'
                              'int main(void){return audit_fixture_symbol();}\n')
            consumer = root / 'consumer'
            subprocess.check_call(['gcc', str(source), '-L' + temp, '-lfixture',
                                   '-Wl,-rpath,$ORIGIN', '-o', str(consumer)])
            alias = root / 'build-id-alias'
            alias.symlink_to(consumer.name)
            missing = root / 'missing-link'
            missing.symlink_to('absent.so')
            audit = root / 'symbol-audit.json'
            audit.write_text(json.dumps({'audit_version': 3, 'elf_files_scanned': 2,
                'direct_import_matches': [{'path': str(alias), 'symbols': ['audit_fixture_symbol']}],
                'errors': [{'path': str(missing), 'kind': 'broken_symlink'}]}))
            (root / 'transaction-symbols.json').write_text(json.dumps({'libraries': [
                {'library': str(library), 'scan_symbols': ['audit_fixture_symbol']}]}))
            before = sorted(p.name for p in root.iterdir())
            result = DIAG.collect(audit)
            match = result['matches'][0]
            self.assertEqual(match['resolved_path'], str(consumer))
            self.assertTrue(any(not s['defined'] for s in match['target_symbols']))
            dependency = next(d for d in match['direct_dependency_candidates'] if d['needed'] == 'libfixture.so')
            self.assertEqual(len(dependency['candidates']), 1)
            self.assertTrue(dependency['candidates'][0]['target_symbols'][0]['defined'])
            self.assertEqual(len(result['removal_libraries']), 1)
            self.assertFalse(result['other_errors'][0]['current']['exists'])
            self.assertTrue(missing.is_symlink())
            self.assertEqual(sorted(p.name for p in root.iterdir()), before)
            self.assertNotIn('safe_to_install', result)

    def test_dynamic_loader_tokens_remain_explicitly_unresolved(self):
        consumer = {'resolved_path': '/opt/example/bin/app',
                    'search_paths': [{'kind': 'RUNPATH', 'value': '$ORIGIN/$LIB:relative'}]}
        unused, unresolved = DIAG.dependency_candidates(consumer, 'lib-no-such-fixture.so', {})
        self.assertEqual(unresolved, ['/opt/example/bin/$LIB', 'relative'])


if __name__ == '__main__':
    unittest.main()
