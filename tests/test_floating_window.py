"""Instancia única y toggle reales en D-Bus privado, sin audio ni sesión real."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FloatingTests(unittest.TestCase):
    def test_second_launch_toggles_same_window(self):
        with tempfile.TemporaryDirectory(prefix='nerv-window-') as folder:
            config = Path(folder) / 'bus.conf'
            config.write_text('<busconfig><type>session</type><listen>unix:path=' + folder
                + '/bus</listen><auth>EXTERNAL</auth><policy context="default">'
                + '<allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/>'
                + '</policy></busconfig>')
            bus = subprocess.Popen(['dbus-daemon', '--nofork', '--print-address=1',
                '--config-file=' + str(config)], stdout=subprocess.PIPE, text=True)
            app = None
            try:
                address = bus.stdout.readline().strip()
                self.assertTrue(address)
                env = {**os.environ, 'DBUS_SESSION_BUS_ADDRESS': address,
                       'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'}
                command = [sys.executable, str(ROOT / 'widget/contents/tools/nerv_deck.py')]
                app = subprocess.Popen(command, env=env, stderr=subprocess.PIPE, text=True)
                def call(method):
                    return subprocess.run(['gdbus', 'call', '--session', '--dest',
                        'com.xfunbox.NervDeck', '--object-path', '/NervDeck',
                        '--method', 'com.xfunbox.NervDeck.' + method], env=env, capture_output=True, text=True)
                for _ in range(100):
                    state = call('State')
                    if state.returncode == 0:
                        break
                    if app.poll() is not None:
                        self.fail(app.stderr.read())
                    time.sleep(.03)
                self.assertEqual(state.returncode, 0, state.stderr)
                def visible():
                    return json.loads(ast.literal_eval(call('State').stdout)[0])['visible']
                self.assertTrue(visible())
                subprocess.run(command, env=env, check=True, capture_output=True, timeout=10)
                self.assertFalse(visible())
                self.assertIsNone(app.poll())
                subprocess.run(command, env=env, check=True, capture_output=True, timeout=10)
                self.assertTrue(visible())
                call('Quit')
                app.wait(timeout=5)
                errors = app.stderr.read()
                self.assertNotIn('.qml:', errors)
                self.assertEqual(app.returncode, 0, errors)
            finally:
                if app is not None and app.poll() is None:
                    app.terminate()
                    app.wait(timeout=5)
                bus.terminate()
                bus.wait(timeout=5)
                bus.stdout.close()
                if app is not None:
                    app.stderr.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
