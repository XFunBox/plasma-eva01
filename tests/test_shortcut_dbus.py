"""Regresión del protocolo Qt real: bus privado y daemon sin acceso al escritorio."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DAEMON = Path('/usr/lib/x86_64-linux-gnu/libexec/kglobalacceld')
spec = importlib.util.spec_from_file_location('shortcut_protocol', ROOT / 'instalar-ventana.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@unittest.skipUnless(DAEMON.is_file() and shutil.which('dbus-daemon') and shutil.which('gdbus'),
                     'Necesita KGlobalAccel y D-Bus')
class ShortcutProtocolTests(unittest.TestCase):
    def test_register_remove_register_on_private_daemon(self):
        with tempfile.TemporaryDirectory(prefix='nerv-shortcut-test-') as temp:
            root = Path(temp)
            config = root / 'bus.conf'
            config.write_text('<busconfig><type>session</type><listen>unix:path=' + temp
                + '/bus</listen><auth>EXTERNAL</auth><policy context="default">'
                + '<allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/>'
                + '</policy></busconfig>')
            env = dict(os.environ)
            env.pop('DISPLAY', None)
            env.pop('WAYLAND_DISPLAY', None)
            env.update(HOME=temp, DBUS_SESSION_BUS_ADDRESS='', QT_QPA_PLATFORM='offscreen',
                       XDG_SESSION_TYPE='x11', XDG_CONFIG_HOME=temp + '/config',
                       XDG_DATA_HOME=temp + '/data', XDG_CACHE_HOME=temp + '/cache',
                       XDG_RUNTIME_DIR=temp + '/run')
            Path(env['XDG_RUNTIME_DIR']).mkdir(mode=0o700)
            entry = Path(env['XDG_DATA_HOME']) / 'kglobalaccel' / module.DESKTOP
            entry.parent.mkdir(parents=True)
            entry.write_text('[Desktop Entry]\nType=Application\nName=NERV Test\nExec=/bin/true\n')
            daemon = None
            with (root / 'daemon.log').open('w+') as log:
                bus = subprocess.Popen(['dbus-daemon', '--nofork', '--print-address=1',
                    '--config-file=' + str(config)], stdout=subprocess.PIPE, text=True)
                try:
                    address = bus.stdout.readline().strip()
                    self.assertTrue(address, 'No se pudo abrir el bus de prueba privado')
                    env['DBUS_SESSION_BUS_ADDRESS'] = address
                    daemon = subprocess.Popen([str(DAEMON)], env=env, stdout=log, stderr=log)
                    with patch.dict(os.environ, env, clear=True):
                        for _ in range(100):
                            if daemon.poll() is not None:
                                self.fail('El daemon terminó antes de la prueba')
                            try:
                                module.dbus('shortcutKeys', module.action_arg())
                                break
                            except subprocess.CalledProcessError:
                                time.sleep(.02)
                        else:
                            self.fail('KGlobalAccel no registró el servicio privado')
                        for _ in range(3):
                            # Offscreen no captura teclas: comprobamos el protocolo y la supervivencia.
                            module.set_keys([[module.KEY]])
                            self.assertIsNone(daemon.poll())
                            module.dbus('shortcutKeys', module.action_arg())
                            module.restore_keys({'keys': []})
                        module.set_keys([[module.KEY, module.KEY]])
                        self.assertIsNone(daemon.poll())
                finally:
                    if daemon is not None and daemon.poll() is None:
                        daemon.terminate()
                        daemon.wait(timeout=5)
                    bus.terminate()
                    bus.wait(timeout=5)
                    bus.stdout.close()
                log.seek(0)
                self.assertNotIn('type invalid', log.read())


if __name__ == '__main__':
    unittest.main(verbosity=2)
