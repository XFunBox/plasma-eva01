"""Reglas reales en XDG temporal, sin contactar con el compositor del usuario."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('eva_layout', Path(__file__).resolve().parents[1] / 'assets/escritorio/layout.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


class DesktopLayoutTests(unittest.TestCase):
    def test_force_rules_scale_and_preserve_foreign_rules(self):
        panel = dict(size=dict(width=2560, height=1440), scale=1.4, pos=dict(x=1829, y=0))
        self.assertEqual(layout.logical_rect(panel, layout.RECTS['terminal']), (2686, 607, 929, 336))
        real_run = subprocess.run
        def run(command, **kwargs):
            if command[0] == 'qdbus6':
                return subprocess.CompletedProcess(command, 0)
            return real_run(command, **kwargs)
        with tempfile.TemporaryDirectory(prefix='eva reglas ') as tmp:
            env = dict(QT_QPA_PLATFORM='offscreen', XDG_CONFIG_HOME=tmp + '/config', XDG_STATE_HOME=tmp + '/state')
            path = Path(env['XDG_CONFIG_HOME']) / 'kwinrulesrc'
            path.parent.mkdir()
            old = '[General]\nrules=ajena\ncount=1\n[ajena]\nwmclass=otra-app\nposition=9,9\n'
            path.write_text(old)
            with patch.dict(os.environ, env), patch.object(layout.subprocess, 'run', side_effect=run):
                layout.install_rules(panel)
                layout.install_rules(panel)
            def read(group, key):
                return subprocess.check_output(['kreadconfig6', '--file', str(path), '--group', group, '--key', key], text=True, env=dict(os.environ, QT_QPA_PLATFORM='offscreen')).strip()
            self.assertEqual(read('ajena', 'position'), '9,9')
            self.assertEqual(read('General', 'count'), '4')
            self.assertEqual(read('eva01-desktop-terminal', 'position'), '2686,607')
            self.assertEqual(read('eva01-desktop-terminal', 'positionrule'), '2')
            self.assertEqual(read('eva01-desktop-terminal', 'layer'), '1')
            self.assertEqual(read('eva01-desktop-terminal', 'layerrule'), '2')
            self.assertEqual(read('eva01-desktop-archivos', 'sizerule'), '2')
            self.assertEqual(read('eva01-desktop-archivos', 'maximizevert'), 'false')
            self.assertEqual((Path(env['XDG_STATE_HOME']) / 'eva01-desktop/kwinrulesrc.before').read_text(), old)
