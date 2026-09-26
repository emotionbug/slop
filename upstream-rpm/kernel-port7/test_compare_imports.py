import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'compare', Path(__file__).with_name('compare-imports.py'))
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)


class CompareImportsTests(unittest.TestCase):
    def test_each_import_has_one_auditable_outcome(self):
        providers = {'same': {'crc': 1, 'source': 'kernel'},
                     'changed': {'crc': 2, 'source': 'kernel'}}
        result = compare.compare({'same': 1, 'changed': 3, 'gone': 4}, providers)
        self.assertEqual(result['matches'], ['same'])
        self.assertEqual(result['missing'], ['gone'])
        self.assertEqual(result['mismatches']['changed']['actual'], '0x2')
        self.assertEqual(result['import_count'], 3)


if __name__ == '__main__':
    unittest.main()
