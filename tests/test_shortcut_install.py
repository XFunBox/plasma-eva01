"""Copias limitadas a los dos accesos y restauración del atajo propio."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('shortcut_install', ROOT / 'instalar-ventana.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ShortcutTests(unittest.TestCase):
    def test_backup_restore_preserves_bytes_modes_and_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temp:
            roots = {name: Path(temp) / name for name in ('data', 'state')}
            first, second = module.targets(roots)
            first.parent.mkdir(parents=True)
            first.write_bytes(b'previous\x00desktop')
            first.chmod(0o640)
            other = first.parent / 'unrelated.desktop'
            other.write_text('keep')
            with patch.object(module, 'dbus', return_value=[([123],)]):
                state = module.snapshot(roots)
                folder = module.backup(roots, state)
            first.write_text('changed')
            second.parent.mkdir(parents=True)
            second.write_text('new')
            desired = module.read_backup(folder, roots)
            module.restore_files(roots, desired)
            self.assertEqual(first.read_bytes(), b'previous\x00desktop')
            self.assertEqual(first.stat().st_mode & 0o777, 0o640)
            self.assertFalse(second.exists())
            self.assertEqual(other.read_text(), 'keep')
            with patch.object(module, 'set_keys', return_value=[([123],)]) as setter:
                module.restore_keys(desired)
                setter.assert_called_once_with([[123]])
            (folder / 'manifest.json').write_text('{}')
            with self.assertRaises(ValueError):
                module.read_backup(folder, roots)

    def test_conflict_is_rejected_and_new_action_can_be_removed(self):
        with patch.object(module, 'dbus', side_effect=[False, ['other.desktop', '_launch']]):
            with self.assertRaises(ValueError):
                module.check_available()
        with patch.object(module, 'dbus') as call:
            module.restore_keys({'keys': []})
            call.assert_called_once_with('unregister', module.DESKTOP, '_launch')

    def test_invalid_sequences_never_reach_dbus(self):
        for keys in ([[1, 2, 3, 4, 5]], [['M']], [[2**31]], [[True]]):
            with self.subTest(keys=keys), patch.object(module, 'dbus') as call:
                with self.assertRaises(ValueError):
                    module.set_keys(keys)
                call.assert_not_called()

    def test_rollback_restores_files_even_when_dbus_is_down(self):
        with patch.object(module, 'restore_keys', side_effect=RuntimeError('bus down')):
            with patch.object(module, 'restore_files') as restore:
                with self.assertRaises(RuntimeError):
                    module.rollback({'data': 'unused'}, {'keys': []})
                restore.assert_called_once_with({'data': 'unused'}, {'keys': []})

    def test_key_arguments_and_restore_conflict(self):
        with patch.object(module, 'dbus', return_value=[([module.KEY, 0, 0, 0],)]) as call:
            self.assertEqual(module.set_keys([[module.KEY]]), [([module.KEY],)])
            call.assert_called_once_with('setShortcutKeys', repr(module.ACTION), '@a(ai) [([201326669, 0, 0, 0],)]', '6')
        with patch.object(module, 'set_keys', return_value=[]):
            with self.assertRaises(ValueError):
                module.restore_keys({'keys': [([123],)]})


if __name__ == '__main__':
    unittest.main(verbosity=2)
