"""Reproductores MPRIS de prueba; ejecutar únicamente en un bus D-Bus aislado."""
import json
import os
import time
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

ROOT = 'org.mpris.MediaPlayer2'
PLAYER = ROOT + '.Player'
PROPS = 'org.freedesktop.DBus.Properties'
DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
commands = []


class Player(dbus.service.Object):
    def __init__(self, suffix, identity, entry, state):
        self.anchor = time.monotonic()
        self.suffix = suffix
        self.private_bus = dbus.bus.BusConnection(os.environ['DBUS_SESSION_BUS_ADDRESS'])
        self.name = dbus.service.BusName(ROOT + '.' + suffix, bus=self.private_bus)
        super().__init__(self.name, '/org/mpris/MediaPlayer2')
        self.root = {'Identity': identity, 'DesktopEntry': entry, 'CanRaise': True,
                     'CanQuit': False, 'HasTrackList': False,
                     'SupportedUriSchemes': dbus.Array(['spotify'], signature='s'),
                     'SupportedMimeTypes': dbus.Array([], signature='s')}
        self.player = {'PlaybackStatus': state, 'LoopStatus': 'None', 'Rate': 1.0,
                       'MinimumRate': 1.0, 'MaximumRate': 1.0, 'Shuffle': False,
                       'Volume': 0.4, 'Position': dbus.Int64(12_000_000),
                       'CanGoNext': True, 'CanGoPrevious': True, 'CanPlay': True,
                       'CanPause': True, 'CanSeek': True, 'CanControl': True,
                       'Metadata': dbus.Dictionary({
                           'mpris:trackid': dbus.ObjectPath('/track/demo'),
                           'mpris:length': dbus.Int64(180_000_000),
                           'xesam:title': '<b>Night Drive</b>',
                           'xesam:artist': dbus.Array(['NERV Ensemble'], signature='s'),
                           'xesam:album': 'After Hours', 'mpris:artUrl': ''}, signature='sv')}

    @dbus.service.method(PROPS, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface == ROOT:
            return self.root
        if interface == PLAYER:
            result = dict(self.player)
            result['Position'] = self.position()
            return result
        return {}

    def position(self):
        elapsed = (time.monotonic() - self.anchor) * 1_000_000 if self.player['PlaybackStatus'] == 'Playing' else 0
        return dbus.Int64(self.player['Position'] + elapsed)

    @dbus.service.method(PROPS, in_signature='ss', out_signature='v')
    def Get(self, interface, key):
        return self.GetAll(interface)[key]

    @dbus.service.method(PROPS, in_signature='ssv')
    def Set(self, interface, key, value):
        target = self.root if interface == ROOT else self.player
        if interface == PLAYER and key in ('PlaybackStatus', 'Position'):
            self.player['Position'] = self.position()
            self.anchor = time.monotonic()
        target[key] = value
        commands.append([self.suffix, key, str(value)])
        self.PropertiesChanged(interface, {key: value}, [])

    @dbus.service.signal(PROPS, signature='sa{sv}as')
    def PropertiesChanged(self, interface, values, invalidated):
        pass

    @dbus.service.method(PLAYER)
    def PlayPause(self):
        state = 'Paused' if self.player['PlaybackStatus'] == 'Playing' else 'Playing'
        self.Set(PLAYER, 'PlaybackStatus', state)

    @dbus.service.method(PLAYER)
    def Next(self):
        commands.append([self.suffix, 'Next'])

    @dbus.service.method(PLAYER)
    def Previous(self):
        commands.append([self.suffix, 'Previous'])

    @dbus.service.method(PLAYER, in_signature='ox')
    def SetPosition(self, track, value):
        self.Set(PLAYER, 'Position', value)

    @dbus.service.method(PLAYER, in_signature='x')
    def Seek(self, offset):
        self.Set(PLAYER, 'Position', self.player['Position'] + offset)

    @dbus.service.method(ROOT)
    def Raise(self):
        commands.append([self.suffix, 'Raise'])


players = {suffix: Player(suffix, identity, entry, status) for suffix, identity, entry, status in [
    ('spotifast.test', 'EVA-01 Audio', 'spotifast', 'Playing'),
    ('spotify.test', 'Spotify', 'spotify', 'Paused'),
    ('vlc.test', 'VLC media player', 'vlc', 'Playing')]}


class Control(dbus.service.Object):
    @dbus.service.method('org.xfunbox.NervDeck.Test', out_signature='s')
    def Commands(self):
        return json.dumps(commands)

    @dbus.service.method('org.xfunbox.NervDeck.Test', in_signature='sb')
    def Capabilities(self, suffix, enabled):
        for key in ['CanGoNext', 'CanGoPrevious', 'CanPlay', 'CanPause', 'CanSeek', 'CanControl']:
            players[suffix].Set(PLAYER, key, bool(enabled))

    @dbus.service.method('org.xfunbox.NervDeck.Test', in_signature='s')
    def Remove(self, suffix):
        player = players.pop(suffix)
        player.remove_from_connection()
        player.private_bus.release_name(ROOT + '.' + suffix)


control = Control(bus, '/test')
test_name = dbus.service.BusName('org.xfunbox.NervDeck.Test', bus=bus)
print('READY', flush=True)
GLib.MainLoop().run()
