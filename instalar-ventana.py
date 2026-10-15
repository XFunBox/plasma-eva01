#!/usr/bin/env python3
"""Acceso y atajo Ctrl+Alt+M de NERV Deck. Simulación salvo --apply."""
import argparse
import ast
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
from instalar import digest, regular_file, roots_from_env, safe_path, write_file

DESKTOP = 'com.xfunbox.nervdeck.desktop'
ACTION = [DESKTOP, '_launch', 'NERV Deck', 'Mostrar u ocultar NERV Deck']
KEY = 201326669  # Qt: Ctrl+Alt+M
FILES = ['applications/' + DESKTOP, 'kglobalaccel/' + DESKTOP]


def dbus(method, *args):
    result = subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.kde.kglobalaccel',
        '--object-path', '/kglobalaccel', '--method', 'org.kde.KGlobalAccel.' + method,
        *args], capture_output=True, text=True, check=True, timeout=10)
    # Las respuestas usadas contienen sólo strings, enteros, booleanos y arrays.
    value = result.stdout.strip().replace('true', 'True').replace('false', 'False')
    value = value.replace('@ai ', '').replace('@as ', '').replace('@a(ai) ', '')
    return ast.literal_eval(value)[0]


def action_arg():
    return repr(ACTION)


def set_keys(keys):
    if any(len(key) > 4 or any(type(n) is not int or not 0 <= n < 2**31 for n in key) for key in keys):
        raise ValueError('Cada secuencia debe contener como máximo cuatro enteros Qt válidos.')
    # KDE lee exactamente cuatro enteros por QKeySequence, incluso con una sola tecla.
    # Un array corto puede abortar el servidor D-Bus (KWin en Wayland).
    padded = [key + [0] * (4 - len(key)) for key in keys]
    encoded = '[' + ', '.join('(' + repr(key) + ',)' for key in padded) + ']'
    result = dbus('setShortcutKeys', action_arg(), '@a(ai) ' + encoded, '6')
    return [([value for value in key[0] if value],) for key in result]


def check_available():
    if (not dbus('isGlobalShortcutAvailable', str(KEY), DESKTOP)
            and dbus('action', str(KEY))[:2] != ACTION[:2]):
        raise ValueError('Ctrl+Alt+M ya está ocupado; no se ha reasignado otro atajo.')


def targets(roots):
    return [safe_path(roots['data'] / name) for name in FILES]


def snapshot(roots):
    entries = []
    for path in targets(roots):
        regular_file(path)
        entries.append(None if not path.exists() else {
            'data': base64.b64encode(path.read_bytes()).decode(), 'mode': path.stat().st_mode & 0o777})
    return {'version': 1, 'roots': {name: str(roots[name]) for name in ('data', 'state')},
            'files': entries, 'keys': dbus('shortcutKeys', action_arg())}


def backup(roots, state):
    directory = safe_path(roots['state'] / 'nerv-deck/shortcuts')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    folder = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S-'), dir=directory))
    raw = (json.dumps(state, indent=2) + '\n').encode()
    write_file(folder / 'manifest.json', raw, 0o600)
    write_file(folder / 'manifest.sha256', digest(raw).encode(), 0o600)
    return folder


def read_backup(folder, roots):
    safe_path(folder)
    if folder.parent != roots['state'] / 'nerv-deck/shortcuts':
        raise ValueError('Copia ajena a las rutas XDG actuales.')
    raw = regular_file(folder / 'manifest.json').read_bytes()
    if digest(raw) != regular_file(folder / 'manifest.sha256').read_text().strip():
        raise ValueError('Checksum de la copia incorrecto.')
    state = json.loads(raw)
    if (set(state) != {'version', 'roots', 'files', 'keys'} or state['version'] != 1
        or state['roots'] != {name: str(roots[name]) for name in ('data', 'state')}
        or not isinstance(state['files'], list) or len(state['files']) != len(FILES)
        or not isinstance(state['keys'], list)):
        raise ValueError('Manifiesto de copia no válido.')
    for item in state['files']:
        if item is not None:
            if (not isinstance(item, dict) or set(item) != {'data', 'mode'}
                or type(item['mode']) is not int or not 0 <= item['mode'] <= 0o777):
                raise ValueError('Archivo de copia no válido.')
            base64.b64decode(item['data'], validate=True)
    for key in state['keys']:
        if not isinstance(key, (tuple, list)) or len(key) != 1 or not isinstance(key[0], list) or any(type(n) is not int for n in key[0]):
            raise ValueError('Atajo de copia no válido.')
    return state


def restore_files(roots, state):
    for path, item in zip(targets(roots), state['files']):
        regular_file(path)
        if item is None:
            path.unlink(missing_ok=True)
        else:
            write_file(path, base64.b64decode(item['data'], validate=True), item['mode'])


def restore_keys(state):
    if state['keys']:
        keys = [[n for n in key[0] if n] for key in state['keys']]
        result = set_keys(keys)
        if result != [(key,) for key in keys]:
            raise ValueError('No se pudo restaurar el atajo anterior; podría estar ocupado.')
    else:
        dbus('unregister', DESKTOP, '_launch')


def rollback(roots, state):
    try:
        restore_keys(state)
    finally:
        # Recuperar los archivos aunque el bus de la sesión haya desaparecido.
        restore_files(roots, state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    roots = roots_from_env()
    paths = targets(roots)
    source = safe_path(roots['data'] / 'plasma/plasmoids/com.xfunbox.nervdeck/contents/tools/nerv_deck.py')
    desired = read_backup(args.restore, roots) if args.restore else None
    if desired is None:
        check_available()
    print(('APLICAR' if args.apply else 'SIMULACIÓN') + ': ' + ('Restaurar acceso NERV Deck' if desired else 'Instalar acceso NERV Deck y Ctrl+Alt+M'))
    for path in paths:
        print(path)
    if not args.apply:
        print('No se ha escrito ningún archivo.')
        return
    if os.geteuid() == 0:
        raise ValueError('Ejecutar con el usuario de la sesión, sin sudo.')
    if desired is None and not regular_file(source).is_file():
        raise ValueError('Instala primero el paquete con instalar-widget.py --apply.')
    before = snapshot(roots)
    folder = backup(roots, before)
    print('Copia previa: ' + str(folder))
    try:
        if desired is not None:
            restore_keys(desired)
            restore_files(roots, desired)
            subprocess.run(['kbuildsycoca6', '--noincremental'], check=True, capture_output=True)
        else:
            # Desktop Entry: escapar cada carácter reservado dentro del argumento entre comillas.
            escaped = str(source).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
            entry = ('[Desktop Entry]\nType=Application\nName=NERV Deck\nComment=Mostrar u ocultar el widget de música\n'
                'Icon=multimedia-player\nTerminal=false\nStartupNotify=true\nCategories=AudioVideo;Audio;\n'
                'X-KDE-Shortcuts=Ctrl+Alt+M\nExec=/usr/bin/python3 "' + escaped + '"\n').encode()
            for path in paths:
                write_file(path, entry)
            subprocess.run(['kbuildsycoca6', '--noincremental'], check=True, capture_output=True)
            result = set_keys([[KEY]])
            if result != [([KEY],)]:
                raise ValueError('KDE no asignó Ctrl+Alt+M; se conserva la copia previa.')
    except Exception as error:
        try:
            rollback(roots, before)
        except Exception as rollback_error:
            raise ValueError(f'{error}; reversión incompleta: {rollback_error}. Copia: {folder}') from error
        raise
    print('Restauración completada.' if desired else 'Acceso y atajo preparados.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        sys.exit(1)
