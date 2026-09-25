import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import remote_guard as g


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch = patch.object(g, 'STATE', Path(self.tmp.name) / 'state.json')
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.state = {'phase': 'watching', 'kernel_release': '7.2.7-linuxoss+',
                      'token': 'correct-token', 'armed_from_boot_id': 'old-boot',
                      'trial_boot_id': 'trial-boot', 'timeout_seconds': 1200,
                      'old_default': '/boot/vmlinuz-old', 'new_kernel': '/boot/vmlinuz-new',
                      'previous_args': ['panic=0', 'rd.retry=360']}
        g.save(self.state)

    def test_wrong_token_never_confirms(self):
        with patch.object(g, 'matches', return_value=False):
            with self.assertRaises(RuntimeError):
                g.confirmation_state()

    def test_armed_but_not_started_guard_never_confirms(self):
        g.save(dict(self.state, phase='armed'))
        with patch.object(g, 'matches', return_value=True):
            with self.assertRaises(RuntimeError):
                g.confirmation_state()

    def test_deadline_is_not_extended_by_late_confirmation(self):
        with patch.object(g, 'matches', return_value=True), patch.object(g, 'boot_id', return_value='trial-boot'), patch.object(g, 'uptime', return_value=1200):
            with self.assertRaises(RuntimeError):
                g.confirmation_state()

    def test_other_boot_cannot_acknowledge_trial(self):
        with patch.object(g, 'matches', return_value=True), patch.object(g, 'boot_id', return_value='another-boot'):
            with self.assertRaises(RuntimeError):
                g.confirmation_state()

    def test_confirm_removes_trial_settings_and_persists_ack(self):
        with patch.object(g, 'run', return_value='') as run, patch.object(g, 'boot_id', return_value='trial-boot'):
            g.confirmed(self.state)
        self.assertEqual(g.load()['phase'], 'confirmed')
        self.assertEqual(g.load()['confirmed_boot_id'], 'trial-boot')
        self.assertTrue(any('--args=panic=0 rd.retry=360' in c[0][0] for c in run.call_args_list))
        self.assertFalse(any('reboot' in c[0][0] for c in run.call_args_list))

    def test_unverified_fallback_never_reboots(self):
        with patch.object(g, 'run', return_value='/boot/vmlinuz-wrong') as run:
            with self.assertRaises(RuntimeError):
                g.rollback(self.state)
        self.assertFalse(any('reboot' in c[0][0] for c in run.call_args_list))
        self.assertEqual(g.load()['phase'], 'watching')

    def test_stuck_next_entry_never_reboots(self):
        def reply(args, **kwargs):
            if args == ['grubby', '--default-kernel']:
                return '/boot/vmlinuz-old'
            return 'next_entry=new'
        with patch.object(g, 'run', side_effect=reply) as run:
            with self.assertRaises(RuntimeError):
                g.rollback(self.state)
        self.assertFalse(any('reboot' in c[0][0] for c in run.call_args_list))

    def test_deadline_persists_reason_before_orderly_reboot(self):
        def reply(args, **kwargs):
            if args == ['grubby', '--default-kernel']:
                return '/boot/vmlinuz-old'
            if 'reboot' in args:
                self.assertEqual(g.load()['phase'], 'rolling-back')
            return ''
        with patch.object(g, 'run', side_effect=reply) as run:
            g.rollback(self.state)
        self.assertEqual(run.call_args[0][0], ['systemctl', '--no-block', 'reboot'])


if __name__ == '__main__':
    unittest.main()
