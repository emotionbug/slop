import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('crosswalk', Path(__file__).with_name('cve-crosswalk.py'))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def record(rules):
    return {'containers': {'cna': {'affected': [{'vendor': 'Linux', 'product': 'Linux', 'versions': rules}]}}}


class CrosswalkTests(unittest.TestCase):
    def test_explicit_default_is_not_called_a_fix(self):
        rule = {'version': '5.10.215', 'lessThan': '5.10.218',
                'versionType': 'semver', 'status': 'affected'}
        data = record([rule])
        data['containers']['cna']['affected'][0]['defaultStatus'] = 'unaffected'
        self.assertEqual(c.evaluate(data, c.version('7.2.7'))[0], 'unaffected-by-cna-default')
        self.assertEqual(c.evaluate(data, c.version('5.10.216'))[0], 'affected-in-candidate')

    def test_defaults_require_comparable_same_scope_data(self):
        rule = {'version': '5.10', 'lessThan': '5.11', 'versionType': 'semver', 'status': 'affected'}
        data = record([rule])
        product = data['containers']['cna']['affected'][0]
        product['defaultStatus'] = 'unaffected'
        for invalid in (dict(rule, changes=[{'at': '5.10.2', 'status': 'unknown'}]),
                        dict(rule, lessThan='6.1-rc1'), dict(rule, versionType='custom'),
                        dict(rule, lessThanOrEqual='6.2'),
                        dict(rule, lessThan='4.1'), dict(rule, lessThan='4.*')):
            product['versions'] = [invalid]
            self.assertEqual(c.evaluate(data, c.version('7.2.7'))[0], 'needs-review')
        product['versions'] = [{'version': 'abcdef', 'versionType': 'git', 'status': 'affected'}]
        self.assertEqual(c.evaluate(data, c.version('7.2.7'))[0], 'needs-review')
        product['versions'] = [rule]
        other = dict(product, programFiles=['another-scope.c'], versions=[
            {'version': 'abcdef', 'versionType': 'git', 'status': 'affected'}])
        data['containers']['cna']['affected'].append(other)
        self.assertEqual(c.evaluate(data, c.version('7.2.7'))[0], 'needs-review')

    def test_wildcard_upper_bound_and_unknown_status(self):
        rule = {'version': '0', 'lessThan': '6.1.*', 'versionType': 'semver', 'status': 'affected'}
        self.assertTrue(c.contains(rule, c.version('5.10.1')))
        self.assertTrue(c.contains(rule, c.version('6.1.99')))
        self.assertFalse(c.contains(rule, c.version('6.2')))
        data = record([dict(rule, version='7.2', lessThan='7.3', status='unknown')])
        data['containers']['cna']['affected'][0]['defaultStatus'] = 'unaffected'
        self.assertEqual(c.evaluate(data, c.version('7.2.7'))[0], 'needs-review')

    def test_stable_fix_does_not_cover_other_branches(self):
        rule = {'version': '6.1.175', 'lessThanOrEqual': '6.1.*', 'versionType': 'semver', 'status': 'unaffected'}
        self.assertEqual(c.evaluate(record([rule]), c.version('6.1.174'))[0], 'needs-review')
        self.assertEqual(c.evaluate(record([rule]), c.version('6.1.175'))[0], 'fixed-in-candidate-release')
        self.assertEqual(c.evaluate(record([rule]), c.version('7.2.7'))[0], 'needs-review')

    def test_mainline_fix_covers_later_release(self):
        rule = {'version': '7.1', 'lessThanOrEqual': '*', 'versionType': 'original_commit_for_fix', 'status': 'unaffected'}
        self.assertEqual(c.evaluate(record([rule]), c.version('7.2.7'))[0], 'fixed-in-candidate-release')

    def test_pre_introduction_is_not_a_fix(self):
        rule = {'version': '0', 'lessThan': '7.3', 'versionType': 'semver', 'status': 'unaffected'}
        self.assertEqual(c.evaluate(record([rule]), c.version('7.2.7'))[0], 'not-introduced-in-candidate')

    def test_conflicting_or_unsupported_data_never_clears(self):
        rule = {'version': '7.2', 'lessThanOrEqual': '*', 'versionType': 'semver', 'status': 'unaffected'}
        conflict = dict(rule, status='affected')
        self.assertEqual(c.evaluate(record([rule, conflict]), c.version('7.2.7'))[0], 'conflicting-cna-ranges')
        rule['changes'] = [{'at': '7.2.6', 'status': 'affected'}]
        self.assertEqual(c.evaluate(record([rule]), c.version('7.2.7'))[0], 'needs-review')
        self.assertIsNone(c.version('7.2.7_linuxoss+'))


if __name__ == '__main__':
    unittest.main()
