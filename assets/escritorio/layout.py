"""Geometría y reglas exclusivas de los tres paneles EVA-01."""
from pathlib import Path
import os
import shutil
import subprocess

RECTS = {
    'terminal': (1200, 850, 1300, 470),
    'btop': (1200, 220, 1300, 590),
    'archivos': (34, 220, 1130, 1100),
}


def logical_rect(panel, rect):
    x, y, width, height = rect
    wr = panel['size']['width'] / panel['scale'] / 2560
    hr = panel['size']['height'] / panel['scale'] / 1440
    return (round(panel['pos']['x'] + x * wr), round(panel['pos']['y'] + y * hr),
            round(width * wr), round(height * hr))


def install_rules(panel):
    """Añade/actualiza solo nuestras reglas y conserva las reglas ajenas."""
    config = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    target = config / 'kwinrulesrc'
    if target.is_symlink():
        raise ValueError('No se admite kwinrulesrc como enlace simbólico')
    if target.exists():
        state = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state') / 'eva01-desktop'
        state.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = state / 'kwinrulesrc.before'
        if not backup.exists():
            shutil.copyfile(target, backup)
            backup.chmod(0o600)
    def write(group, key, value):
        subprocess.run(['kwriteconfig6', '--file', str(target), '--group', group,
                        '--key', key, '--', str(value)], check=True)
    previous = subprocess.check_output(['kreadconfig6', '--file', str(target), '--group',
                                       'General', '--key', 'rules'], text=True).strip().split(',')
    names = ['eva01-desktop-' + name for name in RECTS]
    for name, rect in RECTS.items():
        group = 'eva01-desktop-' + name
        x, y, width, height = logical_rect(panel, rect)
        values = dict(Description=group, wmclass=group, wmclassmatch=1,
                      wmclasscomplete='false', types=4294967295, layer=1, layerrule=2, position=f'{x},{y}', positionrule=2,
                      size=f'{width},{height}', sizerule=2,
                      maximizevert='false', maximizevertrule=2,
                      maximizehoriz='false', maximizehorizrule=2)
        for key, value in values.items():
            write(group, key, value)
    rules = names + [name for name in previous if name and name not in names]
    write('General', 'rules', ','.join(rules))
    write('General', 'count', len(rules))
    subprocess.run(['qdbus6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.reconfigure'], check=True)
