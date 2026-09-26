import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'attach', Path(__file__).with_name('attach-cna-evidence.py'))
attach = importlib.util.module_from_spec(spec)
spec.loader.exec_module(attach)


class AttachCnaEvidenceTests(unittest.TestCase):
    cross = {'linux_cna_commit': 'a' * 40, 'source_sha256': 'b' * 64}

    def item(self, status):
        return {'cve': 'CVE-2099-1', 'status': status,
                'record_path': 'commit:cve/published/2099/CVE-2099-1.json',
                'record_sha256': 'c' * 64, 'matching_ranges': [{'status': 'unaffected'}]}

    def test_fixed_and_nonapplicable_are_distinct(self):
        fixed = attach.review_for(self.item('fixed-in-candidate-release'), self.cross)
        unaffected = attach.review_for(self.item('unaffected-by-cna-default'), self.cross)
        self.assertEqual(fixed['status'], 'fixed')
        self.assertEqual(unaffected['status'], 'not_affected')
        self.assertIn('Non-applicability', unaffected['scope'])
        self.assertNotIn('Non-applicability', fixed['scope'])

    def test_unresolved_is_never_attached(self):
        self.assertIsNone(attach.review_for(self.item('needs-review'), self.cross))
        self.assertIsNone(attach.review_for(self.item('missing-linux-cna-record'), self.cross))


if __name__ == '__main__':
    unittest.main()
