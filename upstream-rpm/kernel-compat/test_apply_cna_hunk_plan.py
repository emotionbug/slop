import importlib.util
from pathlib import Path
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).with_name('apply-cna-hunk-plan.py')
SPEC = importlib.util.spec_from_file_location('apply_cna_hunk_plan', MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HunkEvidenceTest(unittest.TestCase):
    def test_reverse_fuzz_is_not_reported_as_exact(self):
        with mock.patch.object(
                MODULE, 'run_patch',
                side_effect=[(1, 'exact reverse failed'),
                             (0, 'reverse succeeded with fuzz')]):
            complete, actions, failed = MODULE.evaluate_hunks(
                Path('.'), [('file.c', b'patch')], fuzz=2, apply=False)
        self.assertTrue(complete)
        self.assertIsNone(failed)
        self.assertEqual(actions[0]['action'], 'already-present-fuzzy-2')

    def test_exact_reverse_stays_exact(self):
        with mock.patch.object(
                MODULE, 'run_patch', return_value=(0, 'exact reverse')):
            complete, actions, failed = MODULE.evaluate_hunks(
                Path('.'), [('file.c', b'patch')], fuzz=2, apply=False)
        self.assertTrue(complete)
        self.assertIsNone(failed)
        self.assertEqual(actions[0]['action'], 'already-present-exact')


if __name__ == '__main__':
    unittest.main()
