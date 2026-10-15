"""Prueba el backend QML real con MPRIS real en un bus privado, sin audio."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NervDeckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # El único bus de Qt se inicializa después de fijar esta dirección privada.
        cls.temp = tempfile.TemporaryDirectory(prefix='nerv-deck-test-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.old_bus = os.environ.get('DBUS_SESSION_BUS_ADDRESS')
        config = Path(cls.temp.name) / 'bus.conf'
        config.write_text('<busconfig><type>session</type><listen>unix:path=' + cls.temp.name
            + '/bus</listen><auth>EXTERNAL</auth><policy context="default">'
            + '<allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/>'
            + '</policy></busconfig>')
        cls.daemon = subprocess.Popen(['dbus-daemon', '--nofork', '--print-address=1',
            '--config-file=' + str(config)], stdout=subprocess.PIPE, text=True)
        cls.addClassCleanup(lambda: cls.daemon.terminate() if cls.daemon.poll() is None else None)
        os.environ['DBUS_SESSION_BUS_ADDRESS'] = cls.daemon.stdout.readline().strip()
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        os.environ['QT_QUICK_BACKEND'] = 'software'
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtQml import QQmlEngine, QQmlComponent
        from PyQt6.QtCore import QUrl
        from PyQt6.QtCore import qInstallMessageHandler
        cls.qml_warnings = []
        def capture(_type, _context, message):
            if '.qml:' in message:
                cls.qml_warnings.append(message)
            print(message, file=sys.stderr)
        cls.old_handler = qInstallMessageHandler(capture)
        cls.addClassCleanup(lambda: qInstallMessageHandler(cls.old_handler))
        cls.app = QGuiApplication.instance() or QGuiApplication([])
        cls.engine = QQmlEngine()
        cls.component = QQmlComponent(cls.engine, QUrl.fromLocalFile(str(ROOT / 'widget/contents/ui/MediaController.qml')))
        assert not cls.component.isError(), '\n'.join(e.toString() for e in cls.component.errors())
        cls.controller = cls.component.create()
        assert cls.controller is not None
        cls.fake = subprocess.Popen([sys.executable, str(ROOT / 'tests/fake_mpris.py')],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        cls.addClassCleanup(lambda: cls.fake.terminate() if cls.fake.poll() is None else None)
        assert cls.fake.stdout.readline().strip() == 'READY', cls.fake.stderr.read()
        from PyQt6.QtDBus import QDBusConnection, QDBusInterface
        cls.control = QDBusInterface('org.xfunbox.NervDeck.Test', '/test',
            'org.xfunbox.NervDeck.Test', QDBusConnection.sessionBus())

    @classmethod
    def tearDownClass(cls):
        cls.fake.terminate()
        cls.fake.wait(timeout=5)
        cls.daemon.terminate()
        cls.daemon.wait(timeout=5)
        cls.temp.cleanup()
        if cls.old_bus is None:
            os.environ.pop('DBUS_SESSION_BUS_ADDRESS', None)
        else:
            os.environ['DBUS_SESSION_BUS_ADDRESS'] = cls.old_bus

    def wait_for(self, predicate):
        for _ in range(200):
            self.app.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        self.fail('El backend no alcanzó el estado esperado')

    def tearDown(self):
        self.assertEqual(self.qml_warnings, [], '\n'.join(self.qml_warnings))

    def invoke(self, name, *args):
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(self.controller, name, *[Q_ARG('QVariant', a) for a in args])
        for _ in range(10):
            self.app.processEvents()
            time.sleep(0.01)

    def commands(self):
        return json.loads(self.control.call('Commands').arguments()[0])

    def test_01_discovers_only_music_players_and_converts_units(self):
        self.wait_for(lambda: self.controller.property('available'))
        self.assertEqual(self.controller.property('playerName'), 'EVA-01 Audio')
        self.assertEqual(self.controller.property('title'), '<b>Night Drive</b>')
        self.assertEqual(self.controller.property('durationMs'), 180_000)
        self.assertGreaterEqual(self.controller.property('positionMs'), 12_000)
        self.assertLess(self.controller.property('positionMs'), 30_000)
        players = self.controller.property('players').toVariant()
        self.assertEqual(len(players), 2)
        self.assertNotIn('VLC media player', [p['label'] for p in players])

    def test_01b_position_advances_without_property_signals(self):
        before = self.controller.property('positionMs')
        self.wait_for(lambda: self.controller.property('positionMs') > before + 500)

    def test_02_transport_seek_volume_shuffle_and_repeat_reach_player(self):
        self.invoke('playPause')
        self.wait_for(lambda: not self.controller.property('playing'))
        self.invoke('next')
        self.invoke('previous')
        self.invoke('seekTo', 42_000)
        self.invoke('setVolume', 0.75)
        self.invoke('toggleShuffle')
        self.invoke('cycleRepeat')
        events = self.commands()
        self.assertIn(['spotifast.test', 'Next'], events)
        self.assertIn(['spotifast.test', 'Previous'], events)
        self.assertIn(['spotifast.test', 'Position', '42000000'], events)
        self.assertIn(['spotifast.test', 'Volume', '0.75'], events)
        self.assertIn(['spotifast.test', 'Shuffle', '1'], events)
        self.assertIn(['spotifast.test', 'LoopStatus', 'Track'], events)

    def test_03_disabling_capabilities_blocks_commands(self):
        self.control.call('Capabilities', 'spotifast.test', False)
        self.wait_for(lambda: not self.controller.property('canPlayPause'))
        before = self.commands()
        for method in ['playPause', 'next', 'previous', 'toggleShuffle', 'cycleRepeat']:
            self.invoke(method)
        self.invoke('setVolume', 0.2)
        self.invoke('seekTo', 3_000)
        self.assertEqual(self.commands(), before)
        self.control.call('Capabilities', 'spotifast.test', True)
        self.wait_for(lambda: self.controller.property('canPlayPause'))

    def test_04_switch_and_player_disappearing(self):
        players = self.controller.property('players').toVariant()
        index = next(i for i, p in enumerate(players) if p['label'] == 'Spotify')
        self.invoke('selectPlayer', index)
        self.wait_for(lambda: self.controller.property('playerName') == 'Spotify')
        self.control.call('Remove', 'spotify.test')
        self.wait_for(lambda: self.controller.property('playerName') == 'EVA-01 Audio')
        self.control.call('Remove', 'spotifast.test')
        self.wait_for(lambda: not self.controller.property('available'))
        self.assertEqual(self.controller.property('positionMs'), 0)
        self.assertFalse(self.controller.property('canSeek'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
