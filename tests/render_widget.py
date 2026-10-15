"""Render de la UI real con datos ficticios; no usa MPRIS ni controla aplicaciones."""
import argparse
import os
from pathlib import Path
import sys

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_QUICK_BACKEND'] = 'software'
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mode', choices=['compact', 'expanded', 'idle'], default='compact')
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
app = QGuiApplication([])
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty('previewMode', args.mode)
engine.rootContext().setContextProperty('capturePath', str(args.output.absolute()))
engine.quit.connect(app.quit)
engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('preview_nerv_deck.qml'))))
if not engine.rootObjects():
    sys.exit(1)
QTimer.singleShot(5000, lambda: app.exit(1))
code = app.exec()
if not args.output.is_file():
    sys.exit('No se generó la captura')
sys.exit(code)
