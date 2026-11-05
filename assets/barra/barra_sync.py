#!/usr/bin/python3
"""Sincroniza favoritos de los dos paneles EVA mediante la API de Plasma."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

QUERY = '''print(JSON.stringify(panels().filter(p => %s.includes(p.id)).map(p => {
 const w=p.widgets("org.kde.plasma.icontasks")[0];
 if (!w) return null;
 w.currentConfigGroup=["General"];
 return {id:String(p.id),launchers:w.readConfig("launchers",[])};
}).filter(Boolean)))'''

def evaluate(script):
    result = subprocess.run(['qdbus6', 'org.kde.plasmashell', '/PlasmaShell',
        'org.kde.PlasmaShell.evaluateScript', script], check=True,
        capture_output=True, text=True, timeout=10)
    return result.stdout.strip()

def snapshot(panel_ids):
    data = json.loads(evaluate(QUERY % json.dumps(panel_ids)))
    if not isinstance(data, list):
        raise ValueError('Respuesta de Plasma inválida')
    current = {}
    for row in data:
        if not isinstance(row, dict) or row.get('id') not in {str(p) for p in panel_ids} or row['id'] in current:
            raise ValueError('Panel ajeno o duplicado en respuesta de Plasma')
        values = row['launchers']
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise ValueError('Lista de favoritos inválida')
        current[row['id']] = values
    return current

def choose(current, previous, canonical):
    """Un cambio gana; dos cambios diferentes se conservan para resolución manual."""
    changed = [value for key, value in current.items()
               if key in previous and value != previous[key]]
    if changed:
        return changed[0] if all(v == changed[0] for v in changed) else None
    # Un panel ausente no convierte un conflicto pendiente en consenso.
    prior = list(previous.values())
    if prior and any(value != prior[0] for value in prior[1:]):
        return None
    known = [value for key, value in current.items() if key in previous]
    if known and any(value != known[0] for value in known[1:]):
        return None  # Un conflicto pendiente no se resuelve por un guardado ajeno.
    return canonical

def apply(values, current):
    targets = [int(key) for key, old in current.items() if old != values]
    if not targets:
        return
    # JSON serializa también rutas/URI con caracteres especiales, sin shell.
    script = '''const ids=%s; const values=%s;
    for (const p of panels().filter(p=>ids.includes(p.id))) {
      const w=p.widgets("org.kde.plasma.icontasks")[0];
      if(w){w.currentConfigGroup=["General"];w.writeConfig("launchers",values);w.reloadConfig();}
    }
    print("ok");''' % (json.dumps(targets), json.dumps(values))
    if evaluate(script) != 'ok':
        raise RuntimeError('Plasma no confirmó la actualización')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--panels', type=int, nargs='+', required=True,
                        help='Paneles de aplicaciones; el primero aporta los favoritos iniciales')
    args = parser.parse_args()
    if any(p <= 0 for p in args.panels) or len(set(args.panels)) != len(args.panels) or len(args.panels) < 2:
        parser.error('Selecciona al menos dos identificadores positivos distintos')
    panel_ids = args.panels
    from PyQt6.QtCore import QCoreApplication, QFileSystemWatcher, QTimer
    app = QCoreApplication(sys.argv)
    config = Path(os.environ.get('XDG_CONFIG_HOME') or str(Path.home()/'.config'))/'plasma-org.kde.plasma.desktop-appletsrc'
    state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state')))/'eva-panel-sync'/('state-'+'-'.join(map(str, sorted(panel_ids)))+'.json')
    try:
        saved = json.loads(state.read_text())
        previous, canonical = saved['observed'], saved['launchers']
    except (OSError, ValueError, KeyError):
        previous, canonical = {}, None
    watcher = QFileSystemWatcher([str(config.parent)])
    timer = QTimer(); timer.setSingleShot(True); timer.setInterval(600)
    retry = QTimer(); retry.setSingleShot(True); retry.setInterval(5000)
    signature = None
    def arm(*_):
        nonlocal signature
        if config.exists() and str(config) not in watcher.files():
            watcher.addPath(str(config))
        try:
            st = config.stat(); new = (st.st_ino, st.st_size, st.st_mtime_ns)
        except OSError:
            return
        if new != signature:
            signature = new
            timer.start()
    def sync():
        nonlocal previous, canonical
        try:
            current = snapshot(panel_ids)
            if not current:
                return
            if canonical is None:
                canonical = current.get(str(panel_ids[0]))
                if canonical is None:
                    raise RuntimeError('El panel de referencia todavía no está disponible')
            selected = choose(current, previous, canonical)
            if selected is None:
                print('Cambios simultáneos distintos: se conservan ambas barras; el siguiente cambio resolverá el conflicto.', flush=True)
            else:
                apply(selected, current)
                verified = snapshot(panel_ids) if any(v != selected for v in current.values()) else current
                if any(v != selected for v in verified.values()):
                    raise RuntimeError('Favoritos no coinciden tras aplicar')
                canonical, current = selected, verified
            previous = {**previous, **current} if selected is None else current
            state.parent.mkdir(parents=True, exist_ok=True)
            temp = state.with_suffix('.tmp')
            temp.write_text(json.dumps({'launchers':canonical, 'observed':previous})+'\n')
            temp.chmod(0o600); temp.replace(state)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, RuntimeError) as exc:
            print('Sincronización pendiente: '+str(exc), flush=True)
            retry.start()
    watcher.fileChanged.connect(arm); watcher.directoryChanged.connect(arm)
    timer.timeout.connect(sync); retry.timeout.connect(sync)
    arm(); QTimer.singleShot(0, sync)
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
