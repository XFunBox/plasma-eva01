#!/usr/bin/env python3
"""Barra EVA opcional: simulación por defecto, paneles explícitos y copia restaurable."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import uuid

spec = importlib.util.spec_from_file_location('eva_core', Path(__file__).with_name('instalar.py'))
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
ASSETS = Path(__file__).resolve().parent / 'assets/barra'
THEME = 'plasma/desktoptheme/eva-islas-estados/'
UNIT = 'eva-panel-sync.service'
LAYOUT_FILE = 'plasma-org.kde.plasma.desktop-appletsrc'
PROPS = ('screen', 'location', 'alignment', 'height', 'offset', 'hiding', 'floating',
         'lengthMode', 'minimumLength', 'maximumLength')
OWNER = 'eva01InstallOwner'
BASE_TARGETS = [('config', 'plasmarc'), ('config', LAYOUT_FILE),
                ('config', 'systemd/user/' + UNIT), ('config', 'eva-panel-sync/paneles.json'),
                ('data', 'eva-panel-sync/barra_sync.py')]


def run(command):
    return subprocess.run(command, check=True, text=True, capture_output=True, timeout=30)


def evaluate(script):
    return json.loads(run(['qdbus6', 'org.kde.plasmashell', '/PlasmaShell',
                          'org.kde.PlasmaShell.evaluateScript', script]).stdout.strip())


def service_status():
    result = subprocess.run(['systemctl', '--user', 'show', UNIT,
                             '--property=LoadState', '--property=UnitFileState',
                             '--property=ActiveState'], check=True, text=True,
                            capture_output=True, timeout=10)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if set(values) != {'LoadState', 'UnitFileState', 'ActiveState'}:
        raise ValueError('No se pudo comprobar el estado de ' + UNIT)
    return {'enabled': values['UnitFileState'] in ('enabled', 'enabled-runtime'),
            'active': values['ActiveState'] == 'active'}


def query():
    return evaluate('''print(JSON.stringify(panels().map(function(p) {
      var properties={}, names=%s;
      for(var i=0;i<names.length;i++) if(p[names[i]]!==undefined) properties[names[i]]=p[names[i]];
      p.currentConfigGroup=[];
      return {id:p.id,properties:properties,owner:p.readConfig(%s,""),
        widgets:p.widgets().map(function(w){return {id:w.id,type:w.type};})};
    })));''' % (json.dumps(PROPS), json.dumps(OWNER)))


def make_plan(roots, ids):
    copies = {}
    source = core.safe_path(ASSETS / 'tema')
    if not source.is_dir():
        raise ValueError('Falta el tema de la barra')
    for path in sorted(source.rglob('*')):
        core.safe_path(path)
        if path.is_file():
            copies[('data', THEME + path.relative_to(source).as_posix())] = path.read_bytes()
    if not copies or not (source / 'metadata.json').is_file():
        raise ValueError('Tema incompleto: falta metadata.json')
    copies[('data', 'eva-panel-sync/barra_sync.py')] = core.regular_file(ASSETS / 'barra_sync.py').read_bytes()
    # systemd no interpreta shell y necesita duplicar el especificador %.
    script = str(roots['data'] / 'eva-panel-sync/barra_sync.py')
    if any(c in script for c in '\n\r\0'):
        raise ValueError('Ruta de servicio no válida')
    quoted = '"' + script.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'
    unit = ('[Unit]\nDescription=Favoritos de paneles EVA-01\nAfter=plasma-plasmashell.service\nPartOf=graphical-session.target\n'
            '[Service]\nType=simple\nExecStart=/usr/bin/python3 ' + quoted + ' --panels '
            + ' '.join(map(str, ids)) + '\nRestart=on-failure\nRestartSec=5\n'
            '[Install]\nWantedBy=graphical-session.target\n')
    copies[('config', 'systemd/user/' + UNIT)] = unit.encode()
    copies[('config', 'eva-panel-sync/paneles.json')] = (json.dumps({'panels': ids}) + '\n').encode()
    return copies


def save_manifest(folder, doc):
    raw = (json.dumps(doc, ensure_ascii=False, indent=2) + '\n').encode()
    core.write_file(folder / 'manifest.json', raw, 0o600)
    core.write_file(folder / 'manifest.sha256', core.digest(raw).encode(), 0o600)


def validate_layout(layout):
    if (not isinstance(layout, dict) or set(layout) != {'originals', 'created', 'token', 'service'}
            or not isinstance(layout['token'], str) or not re.fullmatch(r'[a-f0-9]{32}', layout['token'])
            or not isinstance(layout['created'], dict) or not isinstance(layout['originals'], list)
            or len(layout['originals']) < 2
            or not isinstance(layout['service'], dict) or set(layout['service']) != {'enabled', 'active'}
            or any(type(v) is not bool for v in layout['service'].values())):
        raise ValueError('Estado de paneles no válido')
    ids, widgets = set(), set()
    for panel in layout['originals']:
        if (not isinstance(panel, dict) or set(panel) != {'id', 'properties', 'widgets', 'owner'}
                or type(panel['id']) is not int or panel['id'] <= 0 or panel['id'] in ids
                or not isinstance(panel['properties'], dict) or set(panel['properties']) - set(PROPS)
                or not isinstance(panel['widgets'], list) or panel['owner'] != ''):
            raise ValueError('Panel de copia no válido')
        ids.add(panel['id'])
        for name, value in panel['properties'].items():
            if type(value) not in (str, bool, int, float) or isinstance(value, str) and any(c in value for c in '\n\r\0'):
                raise ValueError('Propiedad de panel no válida')
        for widget in panel['widgets']:
            if (not isinstance(widget, dict) or set(widget) != {'id', 'type'} or type(widget['id']) is not int
                    or widget['id'] <= 0 or widget['id'] in widgets or not isinstance(widget['type'], str)):
                raise ValueError('Identificador de widget no válido')
            widgets.add(widget['id'])
    if (any(key not in {str(i) for i in ids} or type(value) is not int or value <= 0 or value in ids
            for key, value in layout['created'].items())
            or len(set(layout['created'].values())) != len(layout['created'])):
        raise ValueError('Identificadores de panel creado no válidos')


def read_backup(folder, roots):
    core.safe_path(folder)
    raw = core.regular_file(folder / 'manifest.json').read_bytes()
    if core.digest(raw) != core.regular_file(folder / 'manifest.sha256').read_text().strip():
        raise ValueError('Manifiesto adulterado')
    doc = json.loads(raw)
    if (not isinstance(doc, dict) or set(doc) != {'version', 'roots', 'components', 'entries', 'layout'}
            or doc['version'] != 1 or doc['components'] != ['barra']
            or doc['roots'] != {key: str(value) for key, value in roots.items()}
            or not isinstance(doc['entries'], list)):
        raise ValueError('Manifiesto no válido o pertenece a otras rutas HOME/XDG')
    validate_layout(doc['layout'])
    seen, previous = set(), []
    for index, entry in enumerate(doc['entries']):
        if not isinstance(entry, dict) or set(entry) != {'root', 'path', 'existed', 'backup', 'sha256', 'mode'}:
            raise ValueError('Entrada de copia no válida')
        root, name = entry['root'], entry['path']
        if (not isinstance(root, str) or not isinstance(name, str)
                or (root, name) not in BASE_TARGETS and not (root == 'data' and name.startswith(THEME)
                    and name != THEME and '..' not in Path(name).parts and Path(name).as_posix() == name and not Path(name).is_absolute())
                or (root, name) in seen or type(entry['existed']) is not bool):
            raise ValueError('Destino no permitido o duplicado')
        seen.add((root, name))
        target = core.regular_file(roots[root] / name)
        data, mode = None, None
        if entry['existed']:
            if entry['backup'] != f'file-{index:03d}' or type(entry['mode']) is not int or not 0 <= entry['mode'] <= 0o777:
                raise ValueError('Ruta o modo de copia no válido')
            data = core.regular_file(folder / entry['backup']).read_bytes()
            if core.digest(data) != entry['sha256']:
                raise ValueError('Archivo de copia adulterado')
            mode = entry['mode']
        elif any(entry[key] is not None for key in ('backup', 'sha256', 'mode')):
            raise ValueError('Entrada ausente no válida')
        # El archivo de Plasma es evidencia, no se sobrescribe: favoritos actuales se conservan.
        if name != LAYOUT_FILE:
            previous.append((target, data, mode))
    if not set(BASE_TARGETS).issubset(seen) or ('data', THEME + 'metadata.json') not in seen:
        raise ValueError('Copia incompleta')
    return doc, previous


def restore_preflight(layout, current):
    originals = {p['id']: p for p in layout['originals']}
    by_id = {p['id']: p for p in current}
    created = {p['id']: p for p in current if p['owner'] == layout['token']}
    for id in layout['created'].values():
        if id in by_id and id not in created:
            raise ValueError('Un panel creado perdió la marca de propiedad; no se retira')
    expected = {w['id']: w['type'] for p in originals.values() for w in p['widgets']}
    if any(p['id'] not in by_id for p in originals.values()):
        raise ValueError('Falta un panel original')
    available = {w['id']: w['type'] for p in current if p['id'] in originals or p['id'] in created for w in p['widgets']}
    if any(available.get(id) != type for id, type in expected.items()):
        raise ValueError('Falta un widget original o cambió de panel ajeno')
    if any(w['id'] not in expected for p in created.values() for w in p['widgets']):
        raise ValueError('Hay widgets ajenos en un panel creado; muévalos antes de restaurar')
    return list(created)


def restore_layout(layout, created):
    evaluate('''var originals=%s, created=%s;
      for(var i=0;i<originals.length;i++) {
        var row=originals[i], p=panelById(row.id);
        for(var j=0;j<row.widgets.length;j++) {
          var id=row.widgets[j].id, found=null, all=panels();
          for(var a=0;a<all.length;a++) {var ws=all[a].widgets();for(var b=0;b<ws.length;b++) if(ws[b].id===id) found=ws[b];}
          var moved=p.addWidget(found); moved.index=j;
        }
        for(var key in row.properties) p[key]=row.properties[key];
      }
      for(var c=0;c<created.length;c++) {var p=panelById(created[c]); if(p.widgets().length) throw Error("Panel no vacío");p.remove();}
      print(JSON.stringify({restored:true}));''' % (json.dumps(layout['originals']), json.dumps(created)))


def install_layout(folder, doc):
    for row in doc['layout']['originals']:
        token = doc['layout']['token']
        result = evaluate('''var p=new Panel; p.currentConfigGroup=[]; p.writeConfig(%s,%s);
          print(JSON.stringify({created:p.id}));''' % (json.dumps(OWNER), json.dumps(token)))
        id = result['created']
        doc['layout']['created'][str(row['id'])] = id
        save_manifest(folder, doc)
        evaluate('''var p=panelById(%s), utility=panelById(%s), screen=%s;
          p.screen=screen;p.location="bottom";p.alignment="center";p.height=52;p.floating=true;p.lengthMode="fit";p.hiding="autohide";p.offset=0;
          utility.screen=screen;utility.location="bottom";utility.alignment="right";utility.height=44;utility.floating=true;utility.lengthMode="fit";utility.hiding="autohide";utility.offset=18;
          var widgets=p.widgets();for(var i=0;i<widgets.length;i++) if(widgets[i].type!=="org.kde.plasma.kickoff" && widgets[i].type!=="org.kde.plasma.icontasks") utility.addWidget(widgets[i]);
          print(JSON.stringify({configured:true}));''' % (row['id'], id, json.dumps(row['properties']['screen'])))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--panels', type=int, nargs='+', metavar='ID')
    parser.add_argument('--restore', type=Path, metavar='COPIA')
    parser.add_argument('--list', action='store_true', help='Consultar paneles e identificadores sin cambios')
    args = parser.parse_args(argv)
    if sum(bool(v) for v in (args.panels, args.restore, args.list)) != 1 or args.list and args.apply:
        parser.error('Use --panels ID ID…, --restore COPIA o --list (excluyentes)')
    if args.panels and (len(args.panels) < 2 or len(set(args.panels)) != len(args.panels) or min(args.panels) <= 0):
        parser.error('Indique al menos dos ID positivos distintos')
    if args.list:
        print(json.dumps(query(), ensure_ascii=False, indent=2));return 0
    roots = core.roots_from_env()
    if args.restore:
        folder = args.restore.absolute()
        doc, previous = read_backup(folder, roots)
        targets = [(entry['root'], entry['path']) for entry in doc['entries']]
    else:
        copies = make_plan(roots, args.panels)
        targets = sorted(set(BASE_TARGETS) | set(copies))
    for root, name in targets:
        core.regular_file(roots[root] / name)
    print(('APLICAR' if args.apply else 'SIMULACIÓN') + (': restaurar barra' if args.restore else ': instalar barra en ' + ', '.join(map(str, args.panels))))
    if not args.apply:
        print('Sin escrituras ni contacto con Plasma. Añada --apply para ejecutar.');return 0
    if os.geteuid() == 0:
        raise ValueError('Ejecute como usuario habitual, sin sudo')
    if not shutil.which('qdbus6') or not shutil.which('systemctl') or not args.restore and not shutil.which('kwriteconfig6'):
        raise ValueError('Faltan herramientas KDE Plasma 6/systemd')
    if not args.restore:
        run(['/usr/bin/python3', '-c', 'from PyQt6.QtCore import QCoreApplication, QFileSystemWatcher, QTimer'])
    current = query()
    if args.restore:
        created = restore_preflight(doc['layout'], current)
        # Copia también el estado inmediatamente anterior a restaurar, sin considerarla instalación.
        recovery, _ = core.backup_targets(roots, targets, ['barra-recovery'])
        print('Copia previa a restaurar: ' + str(recovery), flush=True)
        if service_status()['active']:
            run(['systemctl', '--user', 'stop', UNIT])
        restore_layout(doc['layout'], created)
        if (roots['config'] / 'systemd/user' / UNIT).exists():
            run(['systemctl', '--user', 'disable', UNIT])
        core.restore_snapshot(previous)
        run(['systemctl', '--user', 'daemon-reload'])
        if doc['layout']['service']['enabled']:
            run(['systemctl', '--user', 'enable', UNIT])
        run(['systemctl', '--user', 'restart', 'plasma-plasmashell.service'])
        if doc['layout']['service']['active']:
            run(['systemctl', '--user', 'start', UNIT])
    else:
        rows = [p for id in args.panels for p in current if p['id'] == id]
        if len(rows) != len(args.panels):
            raise ValueError('Falta un panel indicado')
        existing = core.regular_file(roots['config'] / 'eva-panel-sync/paneles.json')
        if existing.exists() or any(p['owner'] for p in rows):
            raise ValueError('Ya existe una instalación; restaure su copia antes de reinstalar')
        for p in rows:
            if sum(w['type'] == 'org.kde.plasma.icontasks' for w in p['widgets']) != 1:
                raise ValueError('Cada panel debe tener exactamente un widget icontasks')
        status = service_status()
        folder, _ = core.backup_targets(roots, targets, ['barra'])
        doc = json.loads((folder / 'manifest.json').read_text())
        doc['layout'] = {'originals': rows, 'created': {}, 'token': uuid.uuid4().hex, 'service': status}
        validate_layout(doc['layout']);save_manifest(folder, doc)
        print('Copia: ' + str(folder), flush=True)
        try:
            if status['active']:
                run(['systemctl', '--user', 'stop', UNIT])
            for (root, name), content in copies.items():
                core.write_file(roots[root] / name, content)
            run(['kwriteconfig6', '--file', str(roots['config'] / 'plasmarc'), '--group', 'Theme', '--key', 'name', '--', 'eva-islas-estados'])
            install_layout(folder, doc)
            run(['systemctl', '--user', 'daemon-reload'])
            run(['systemctl', '--user', 'restart', 'plasma-plasmashell.service'])
            run(['systemctl', '--user', 'enable', '--now', UNIT])
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            print('Instalación parcial. Recupere con: ' + shlex.join([sys.executable, str(Path(__file__).resolve()), '--apply', '--restore', str(folder)]), file=sys.stderr)
            raise
    print('Barra ' + ('restaurada.' if args.restore else 'instalada.'))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print('Error: ' + str(error), file=sys.stderr);sys.exit(1)
