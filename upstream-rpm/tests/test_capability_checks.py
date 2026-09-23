"""Run with EL8 platform-python: verify real RPM dependency semantics."""
import importlib.util
import pathlib
import unittest

path = pathlib.Path(__file__).resolve().parents[1]/'check-rpm-capabilities.py'
spec = importlib.util.spec_from_file_location('checker', str(path))
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def dep(version, flags='=', name='example'):
    return {'capability': name, 'version': version, 'flags': flags}


class DependencySemantics(unittest.TestCase):
    def test_requirement_without_release_matches_release(self):
        self.assertTrue(checker.satisfies(dep('3.3.0'), dep('3.3.0-19.el8')))

    def test_requirement_with_release_is_exact(self):
        self.assertFalse(checker.satisfies(dep('3.3.0-18.el8'), dep('3.3.0-19.el8')))

    def test_epoch_precedes_upstream_version(self):
        self.assertFalse(checker.satisfies(dep('1:1.1.1k-17', '>='), dep('0:4.0.2-1')))

    def test_numeric_version_order(self):
        self.assertTrue(checker.satisfies(dep('10.9', '>='), dep('10.48-1')))

    def test_unversioned_requirement(self):
        self.assertTrue(checker.satisfies(dep('', ''), dep('1.0-1')))

    def test_wrong_soname(self):
        self.assertFalse(checker.satisfies(dep('', '', 'libssl.so.1.1'), dep('', '', 'libssl.so.4')))

    def test_unversioned_provide_requires_solver_review(self):
        self.assertIsNone(checker.satisfies(dep('2.0', '>='), dep('', '')))


if __name__ == '__main__':
    unittest.main()
