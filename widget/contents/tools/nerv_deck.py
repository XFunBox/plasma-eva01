#!/usr/bin/env python3
"""Ventana NERV Deck de instancia única; cada lanzamiento alterna su visibilidad."""
import os
from pathlib import Path
import sys

from PyQt6.QtCore import QObject, QStandardPaths, QUrl, pyqtSlot, QMetaObject, Q_ARG, pyqtClassInfo
from PyQt6.QtDBus import QDBusConnection, QDBusInterface
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine

SERVICE = 'com.xfunbox.NervDeck'
OBJECT = '/NervDeck'


@pyqtClassInfo("D-Bus Interface", "com.xfunbox.NervDeck")
class Control(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window

    @pyqtSlot(str)
    def Toggle(self, token):
        if self.window.isVisible():
            self.window.hide()
        else:
            QMetaObject.invokeMethod(self.window, 'showWithToken', Q_ARG('QVariant', token))

    @pyqtSlot(result=str)
    def State(self):
        import json
        return json.dumps({'visible': self.window.isVisible(), 'active': self.window.isActive()})

    @pyqtSlot()
    def Quit(self):
        QGuiApplication.instance().quit()


def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName('nerv-deck')
    app.setDesktopFileName('com.xfunbox.nervdeck')
    app.setQuitOnLastWindowClosed(False)
    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        sys.exit('NERV Deck necesita el bus D-Bus de la sesión.')
    token = os.environ.pop('XDG_ACTIVATION_TOKEN', '')
    if not bus.registerService(SERVICE):
        remote = QDBusInterface(SERVICE, OBJECT, '', bus)
        reply = remote.call('Toggle', token)
        if reply.errorMessage():
            sys.exit('No se pudo contactar con NERV Deck: ' + reply.errorMessage())
        return 0
    local = Path(__file__).resolve().parents[1] / 'ui/FloatingWindow.qml'
    source = str(local) if local.is_file() else QStandardPaths.locate(
        QStandardPaths.StandardLocation.GenericDataLocation,
        'plasma/plasmoids/com.xfunbox.nervdeck/contents/ui/FloatingWindow.qml')
    if not source:
        sys.exit('Instale primero el paquete del widget NERV Deck.')
    engine = QQmlApplicationEngine()
    engine.load(QUrl.fromLocalFile(source))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    control = Control(window)
    if not bus.registerObject(OBJECT, control, QDBusConnection.RegisterOption.ExportAllSlots):
        sys.exit('No se pudo registrar el control de NERV Deck.')
    control.Toggle(token)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
