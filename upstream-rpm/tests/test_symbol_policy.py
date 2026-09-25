"""Regression fixtures for transaction-specific symbol policy, using real ELF files."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('policy', str(
    Path(__file__).resolve().parents[1] / 'deploy' / 'symbol-policy.py'))
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.provider = self.root / 'libpolicyfixture.so'
        self.consumer = self.root / 'consumer'
        self.owner = 'fixture\t0:1-1\tx86_64'
        (self.root / 'provider.c').write_text('int strlcpy(void){return 0;}\n')
        (self.root / 'consumer.c').write_text('extern int strlcpy(void); int main(void){return strlcpy();}\n')
        self.build()
        self.audit = {'audit_version': 3, 'direct_import_matches': [
            {'path': str(self.consumer), 'aliases': [str(self.consumer)], 'symbols': ['strlcpy']}],
            'errors': [], 'directory_symlinks_outside_roots': []}
        self.removals = {'libraries': [{'library': '/usr/lib64/libmagic.so.1',
                                       'scan_symbols': ['strlcpy', 'strlcat']}]}

    def build(self, versioned=False):
        extra = []
        if versioned:
            version = self.root / 'version.map'
            version.write_text('FIXTURE_1 { global: strlcpy; local: *; };\n')
            extra = ['-Wl,--version-script=' + str(version)]
        subprocess.check_call(['gcc', '-shared', '-fPIC', str(self.root / 'provider.c'),
                               '-Wl,-soname,libpolicyfixture.so', '-o', str(self.provider)] + extra)
        subprocess.check_call(['gcc', str(self.root / 'consumer.c'), '-L' + str(self.root),
                               '-lpolicyfixture', '-o', str(self.consumer)])

    def classify(self, incoming=(), outgoing=None, owners=()):
        with mock.patch.object(POLICY.DETAILS, 'owners', return_value={
                'packages': [self.owner], 'query_error': None}), \
             mock.patch.object(POLICY.DETAILS, 'cached_libraries', return_value={
                'libpolicyfixture.so': [str(self.provider)]}):
            return POLICY.classify(self.audit, self.removals, set(incoming), outgoing or {}, set(owners))

    def test_unchanged_direct_provider_clears_shared_name_only(self):
        result = self.classify()
        self.assertTrue(result['allow_transaction'])
        self.assertEqual(result['accepted_matches'][0]['evidence']['providers']['strlcpy']['path'],
                         str(self.provider))

    def test_provider_replaced_by_transaction_blocks(self):
        self.assertFalse(self.classify(incoming=[str(self.provider)])['allow_transaction'])

    def test_loader_environment_prevents_shared_name_exception(self):
        with mock.patch.dict(os.environ, {'LD_LIBRARY_PATH': '/custom/loader/path'}):
            self.assertFalse(self.classify()['allow_transaction'])

    def test_missing_provider_blocks(self):
        self.provider.unlink()
        self.assertFalse(self.classify()['allow_transaction'])

    def test_versioned_import_is_not_cleared_as_plain_name(self):
        self.build(versioned=True)
        self.assertFalse(self.classify()['allow_transaction'])

    def test_unknown_removed_provider_is_not_cleared(self):
        self.removals['libraries'][0]['library'] = '/usr/lib64/another.so'
        self.assertFalse(self.classify()['allow_transaction'])

    def test_retired_consumer_requires_ownership_and_no_surviving_hardlink(self):
        self.removals['libraries'][0]['library'] = '/usr/lib64/another.so'
        outgoing = {str(self.consumer): 0}
        result = self.classify(outgoing=outgoing, owners=[self.owner])
        self.assertTrue(result['allow_transaction'])
        self.assertFalse(self.classify(outgoing=outgoing)['allow_transaction'])
        self.assertFalse(self.classify(outgoing={str(self.consumer): 1}, owners=[self.owner])['allow_transaction'])
        link = self.root / 'unowned-hardlink'
        os.link(str(self.consumer), str(link))
        self.audit['direct_import_matches'][0]['aliases'].append(str(link))
        self.assertFalse(self.classify(outgoing=outgoing, owners=[self.owner])['allow_transaction'])

    def test_existing_dangling_link_is_warning_but_unreadable_or_uncovered_is_not(self):
        self.audit['direct_import_matches'] = []
        broken = self.root / 'dangling'
        broken.symlink_to('absent')
        self.audit['errors'] = [{'path': str(broken), 'kind': 'broken_symlink'}]
        result = self.classify()
        self.assertTrue(result['allow_transaction'])
        self.assertEqual(len(result['preexisting_dangling_links']), 1)
        self.assertTrue(broken.is_symlink())
        self.audit['errors'].append({'path': '/fixture/unreadable', 'kind': 'permission_denied'})
        self.assertFalse(self.classify()['allow_transaction'])
        self.audit['errors'] = []
        self.audit['directory_symlinks_outside_roots'] = [{'path': '/fixture/outside'}]
        self.assertFalse(self.classify()['allow_transaction'])


if __name__ == '__main__':
    unittest.main()
