import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('stage', Path(__file__).with_name('stage-reviewed-modules.py'))
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class StageSafety(unittest.TestCase):
    def test_exact_source_can_follow_weak_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wrong = base/'extra.ko'; exact = base/'vendor.ko'; weak = base/'weak-updates.ko'
            wrong.write_bytes(b'wrong module')
            exact.write_bytes(b'exact reviewed module')
            weak.symlink_to(exact)
            selected = stage.choose_exact_source(
                (base/'missing.ko', wrong, weak), stage.digest(exact))
            self.assertEqual(selected, weak)

    def test_exact_source_refuses_only_changed_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            changed = Path(tmp)/'changed.ko'
            changed.write_bytes(b'unreviewed module')
            with self.assertRaises(RuntimeError):
                stage.choose_exact_source((changed,), '0'*64)

    def test_exact_copy_retry_and_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); source = base/'source'; dest = base/'modules/test.ko'
            source.write_bytes(b'reviewed module fixture')
            expected = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertTrue(stage.copy_new_exact(source, dest, expected))
            self.assertFalse(stage.copy_new_exact(source, dest, expected))
            dest.write_bytes(b'existing different module')
            with self.assertRaises(RuntimeError): stage.copy_new_exact(source, dest, expected)
            self.assertEqual(dest.read_bytes(), b'existing different module')

    def test_source_change_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); source=base/'source'; dest=base/'dest'
            source.write_bytes(b'new source')
            with self.assertRaises(RuntimeError): stage.copy_new_exact(source, dest, '0'*64)
            self.assertFalse(dest.exists())
            dest.symlink_to(source)
            with self.assertRaises(RuntimeError): stage.copy_new_exact(source, dest, stage.digest(source))

    def test_loaded_identity_is_not_modinfo_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            sysroot=Path(tmp); module=sysroot/'gc_enforcement'; module.mkdir()
            (module/'srcversion').write_text('wrong-weak-update-version\n')
            with self.assertRaises(RuntimeError): stage.check_live_identity(sysroot,'gc_enforcement','srcversion','expected')
            (module/'srcversion').write_text('expected\n')
            stage.check_live_identity(sysroot,'gc_enforcement','srcversion','expected')


if __name__ == '__main__': unittest.main()
