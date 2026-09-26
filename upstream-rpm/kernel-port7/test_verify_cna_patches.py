import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'verify', Path(__file__).with_name('verify-cna-patches.py'))
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)

ancestry_spec = importlib.util.spec_from_file_location(
    'ancestry', Path(__file__).with_name('verify-mainline-ancestry.py'))
ancestry = importlib.util.module_from_spec(ancestry_spec)
ancestry_spec.loader.exec_module(ancestry)


class VerifyCnaPatchesTests(unittest.TestCase):
    def test_short_removed_by_commit_is_recognized(self):
        patch = (b'[There is no upstream commit, as this code was removed by upstream\n'
                 b' commit 044925f9b565 ("remove old code")]\n')
        self.assertEqual(verify.REMOVED_BY.search(patch).group(1), b'044925f9b565')

    def test_exact_reverse_apply_wins(self):
        checks = [
            {'reverse': {'applies': False}, 'forward': {'applies': True}},
            {'reverse': {'applies': True}, 'forward': {'applies': False}},
        ]
        self.assertEqual(verify.classify(checks), 'fix-present-exact-reverse-apply')

    def test_forward_apply_and_drift_are_distinct(self):
        forward = [{'reverse': {'applies': False}, 'forward': {'applies': True}}]
        drift = [{'reverse': {'applies': False}, 'forward': {'applies': False}}]
        self.assertEqual(verify.classify(forward), 'fix-absent-forward-apply')
        self.assertEqual(verify.classify(drift), 'inconclusive-context-drift')

    def test_ancestry_resolves_only_a_proven_ancestor(self):
        proof = [{'is_ancestor': True, 'evidence_kind': 'fix-commit'}]
        removed = [{'is_ancestor': True, 'evidence_kind': 'vulnerable-code-removed'}]
        miss = [{'is_ancestor': False, 'evidence_kind': 'fix-commit'}]
        self.assertEqual(ancestry.resolved_status('inconclusive-context-drift', proof),
                         'fix-present-in-base-tag-ancestry')
        self.assertEqual(ancestry.resolved_status('inconclusive-context-drift', removed),
                         'not-affected-code-removed-in-base-tag')
        self.assertEqual(ancestry.resolved_status('inconclusive-context-drift', miss),
                         'inconclusive-context-drift')


if __name__ == '__main__':
    unittest.main()
