import unittest
import json
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets/barra"))
import barra_sync
from barra_sync import choose
class SyncTests(unittest.TestCase):
 def test_same(self):self.assertEqual(choose({'3':['a'],'22':['a']},{'3':['a'],'22':['a']},['a']),['a'])
 def test_from_first(self):self.assertEqual(choose({'3':['b','a'],'22':['a']},{'3':['a'],'22':['a']},['a']),['b','a'])
 def test_from_second(self):self.assertEqual(choose({'3':['a'],'22':[]},{'3':['a'],'22':['a']},['a']),[])
 def test_conflict(self):self.assertIsNone(choose({'3':['b'],'22':['c']},{'3':['a'],'22':['a']},['a']))
 def test_conflict_persists(self):self.assertIsNone(choose({'3':['b'],'22':['c']},{'3':['b'],'22':['c']},['a']))
 def test_conflict_survives_missing_panel(self):
  self.assertIsNone(choose({'81':['b']}, {'81':['b'],'93':['c']}, ['a']))
 def test_new_panel(self):self.assertEqual(choose({'3':['a'],'22':['x']},{'3':['a']},['a']),['a'])
 def test_restart(self):self.assertEqual(choose({'3':['a'],'22':['b']},{'3':['a'],'22':['a']},['a']),['b'])
 def test_one_absent(self):self.assertEqual(choose({'3':['b']},{'3':['a'],'22':['a']},['a']),['b'])
class PortableSyncTests(unittest.TestCase):
 def test_explicit_panels_filter_and_preserve_empty_launchers(self):
  with patch.object(barra_sync, 'evaluate', return_value='[{"id":"81","launchers":[]}]') as bus:
   self.assertEqual(barra_sync.snapshot([81, 93]), {'81': []})
   self.assertIn('[81, 93]', bus.call_args.args[0])
 def test_rejects_unselected_panel_from_plasma(self):
  with patch.object(barra_sync, 'evaluate', return_value='[{"id":"55","launchers":["private"]}]'):
   with self.assertRaises(ValueError): barra_sync.snapshot([81, 93])
 def test_rejects_duplicate_panel_response(self):
  with patch.object(barra_sync, 'evaluate', return_value='[{"id":"81","launchers":[]},{"id":"81","launchers":[]}]'):
   with self.assertRaises(ValueError): barra_sync.snapshot([81, 93])
 def test_no_update_when_already_equal(self):
  with patch.object(barra_sync, 'evaluate', side_effect=AssertionError('Unexpected mutation')):
   barra_sync.apply(['applications:test.desktop'], {'81':['applications:test.desktop']})
if __name__=='__main__':unittest.main()
