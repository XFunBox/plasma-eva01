#!/usr/bin/python3
"""Tres aplicaciones dedicadas en la capa del escritorio de XWayland."""
import argparse, configparser, fcntl, json, os, subprocess, time
from pathlib import Path
from Xlib import X, Xatom, display, protocol
from layout import RECTS, install_rules
BASE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', default='eDP-1', help='Nombre de salida de kscreen-doctor')
args = parser.parse_args()
lock = open(BASE / 'running.lock', 'w')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(0)
outputs = json.loads(subprocess.check_output(['kscreen-doctor', '-j'], text=True))['outputs']
panel = next((o for o in outputs if o['name'] == args.output and o['enabled']), None)
if panel is None:
    print('Panel interno desactivado: no se abren los paneles del escritorio.')
    raise SystemExit(0)
kwin = configparser.ConfigParser(strict=False, interpolation=None)
kwin.read(Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'kwinrc')
xscale = kwin.getfloat('Xwayland', 'Scale', fallback=panel['scale'])
install_rules(panel)
d = display.Display()
root = d.screen().root
atom = d.intern_atom

def prop(w, key):
    p = w.get_full_property(atom(key), X.AnyPropertyType)
    return p.value if p is not None else []

def clients():
    return [d.create_resource_object('window', int(i)) for i in prop(root, '_NET_CLIENT_LIST')]

specs = [
    ('terminal', ['konsole', '--separate', '--hide-menubar', '--hide-tabbar', '--profile', 'EVA-01-Escritorio', '--workdir', str(Path.home())], RECTS['terminal'], 1),
    ('btop', ['konsole', '--separate', '--hide-menubar', '--hide-tabbar', '--profile', 'EVA-01-Escritorio', '-p', 'Font=DejaVu Sans Mono,9', '-e', 'btop', '--config', str(BASE / 'btop.conf')], RECTS['btop'], 1),
    ('archivos', ['dolphin', '--new-window', str(Path.home())], RECTS['archivos'], .88),
]
existing = {w.get_wm_class() for w in clients()}
result = []
for name, command, rect, opacity in specs:
    cls = 'eva01-desktop-' + name
    if (cls, cls) in existing:
        for w in clients():
            if w.get_wm_class() == (cls, cls):
                w.change_property(atom('_NET_WM_WINDOW_TYPE'), Xatom.ATOM, 32, [atom('_NET_WM_WINDOW_TYPE_DESKTOP')])
        d.sync()
        continue
    env = dict(os.environ, QT_QPA_PLATFORM='xcb', COLORTERM='truecolor', ZDOTDIR=str(BASE / 'zsh'))
    log = open(BASE / (name + '.log'), 'a')
    child = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
    window = None
    for _ in range(100):
        for w in clients():
            if list(prop(w, '_NET_WM_PID')) == [child.pid] and atom('_NET_WM_WINDOW_TYPE_NORMAL') in prop(w, '_NET_WM_WINDOW_TYPE'):
                window = w
                break
        if window is not None:
            break
        if child.poll() is not None:
            break
        time.sleep(.2)
    if window is None:
        raise RuntimeError(f'No se encontró la ventana dedicada de {name}; consultar {name}.log')
    window.set_wm_class(cls, cls)
    window.change_property(atom('_MOTIF_WM_HINTS'), atom('_MOTIF_WM_HINTS'), 32, [2, 0, 0, 0, 0])
    window.change_property(atom('_NET_WM_DESKTOP'), Xatom.CARDINAL, 32, [0xffffffff])
    window.change_property(atom('_NET_WM_WINDOW_OPACITY'), Xatom.CARDINAL, 32, [int(opacity * 0xffffffff)])
    window.change_property(atom('_NET_WM_WINDOW_TYPE'), Xatom.ATOM, 32, [atom('_NET_WM_WINDOW_TYPE_DESKTOP')])
    d.sync()
    # Tipo escritorio con capa Below forzada por reglas: visible sobre Plasma.
    for state in ['_NET_WM_STATE_SKIP_TASKBAR', '_NET_WM_STATE_SKIP_PAGER', '_NET_WM_STATE_BELOW']:
        event = protocol.event.ClientMessage(window=window, client_type=atom('_NET_WM_STATE'), data=(32, [1, atom(state), 0, 1, 0]))
        root.send_event(event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    x, y, width, height = rect
    width_ratio = panel['size']['width'] / panel['scale'] * xscale / 2560
    height_ratio = panel['size']['height'] / panel['scale'] * xscale / 1440
    x = round(panel['pos']['x'] * xscale + x * width_ratio)
    y = round(panel['pos']['y'] * xscale + y * height_ratio)
    width, height = round(width * width_ratio), round(height * height_ratio)
    event = protocol.event.ClientMessage(window=window, client_type=atom('_NET_MOVERESIZE_WINDOW'), data=(32, [(15 << 8) | (1 << 12), x, y, width, height]))
    root.send_event(event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    d.sync()
    result.append({'name': name, 'pid': child.pid, 'window': hex(window.id), 'rect': rect})
if result:
    (BASE / 'windows.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))

subprocess.run(['qdbus6', 'org.kde.KWin', '/Scripting', 'org.kde.kwin.Scripting.unloadScript', 'eva01-desktop-finalize'], stdout=subprocess.DEVNULL, check=True)
subprocess.run(['qdbus6', 'org.kde.KWin', '/Scripting', 'org.kde.kwin.Scripting.loadScript', str(BASE / 'finalize.js'), 'eva01-desktop-finalize'], stdout=subprocess.DEVNULL, check=True)
subprocess.run(['qdbus6', 'org.kde.KWin', '/Scripting', 'org.kde.kwin.Scripting.start'], check=True)
