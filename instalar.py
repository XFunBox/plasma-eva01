#!/usr/bin/env python3
"""Instalador EVA-01 por usuario. Sin --apply, no escribe ningún archivo."""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


COMPONENTS = ("apariencia", "atajos", "ventanas", "terminales")
ASSETS = Path(__file__).resolve().parent / "assets"
SCRIPT = "kwin/scripts/eva01-ordenar-ventanas/"
TARGETS = {
    "apariencia": [("config", "kdeglobals"), ("config", "plasmarc"),
                   ("data", "color-schemes/EVA01Dark.colors")],
    "atajos": [("config", "kglobalshortcutsrc")],
    "ventanas": [("config", "kwinrc"), ("data", SCRIPT + "metadata.json"),
                 ("data", SCRIPT + "contents/code/main.js"),
                 ("data", "applications/eva01-ordenar-ventanas.desktop")],
    "terminales": [("config", "kitty/kitty.conf"), ("config", "kitty/eva01.conf"),
                   ("config", "plasma-eva01/zsh/.zshrc"),
                   ("data", "org.gnome.Ptyxis/palettes/EVA-01.palette"), ("config", "konsolerc"),
                   ("data", "konsole/EVA-01.colorscheme"),
                   ("data", "konsole/EVA-01.profile")],
}
KITTY_BEGIN = "# >>> plasma-eva01 >>>"
KITTY_END = "# <<< plasma-eva01 <<<"


def safe_path(path):
    """Rechaza enlaces y antecesores que no sean directorios."""
    if not path.is_absolute() or ".." in path.parts or any(c in str(path) for c in "\n\r\0"):
        raise ValueError(f"Ruta no válida: {path}")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f"No se admiten enlaces simbólicos: {part}")
        if part != path and part.exists() and not part.is_dir():
            raise ValueError(f"Un antecesor no es un directorio: {part}")
    return path


def regular_file(path):
    safe_path(path)
    if path.exists() and not path.is_file():
        raise ValueError(f"Se esperaba un archivo normal: {path}")
    return path


def roots_from_env():
    home = Path(os.environ.get("HOME", str(Path.home())))
    return {name: safe_path(Path(os.environ.get(env) or str(home / default)))
            for name, env, default in (("config", "XDG_CONFIG_HOME", ".config"),
                                       ("data", "XDG_DATA_HOME", ".local/share"),
                                       ("state", "XDG_STATE_HOME", ".local/state"))}


def selected_targets(components):
    return sorted({target for name in components for target in TARGETS[name]})


def run(command):
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)


def preflight_reload(no_reload):
    if no_reload:
        return
    if not os.environ.get("DBUS_SESSION_BUS_ADDRESS") or not shutil.which("qdbus6"):
        raise ValueError("Se necesita una sesión KDE y qdbus6; use --no-reload para preparar archivos.")
    run(["qdbus6", "org.kde.KWin", "/KWin", "org.kde.KWin.supportInformation"])


def reload_session(components, no_reload):
    if no_reload:
        return
    run(["qdbus6", "org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"])
    if "ventanas" in components:
        run(["qdbus6", "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.start"])


def asset(name):
    path = regular_file(ASSETS / name)
    if not path.exists():
        raise ValueError(f"Falta el recurso: {path}")
    return path.read_bytes()


def make_plan(roots, components):
    """Devuelve contenido y claves; sólo lee, también durante la simulación."""
    copies, settings = {}, []

    def copy(root, target, source):
        copies[(root, target)] = asset(source)

    def setting(file, group, key, value):
        settings.append((file, group, key, value))

    if "apariencia" in components:
        copy("data", "color-schemes/EVA01Dark.colors", "EVA01Dark.colors")
        colors = configparser.ConfigParser(interpolation=None)
        colors.optionxform = str
        colors.read_string(asset("EVA01Dark.colors").decode())
        for group in colors.sections():
            if group.startswith(("Colors:", "ColorEffects:")) or group == "WM":
                for key, value in colors[group].items():
                    setting("kdeglobals", group, key, value)
        setting("kdeglobals", "General", "ColorScheme", "EVA01Dark")
        setting("kdeglobals", "Icons", "Theme", "breeze-dark")
        setting("plasmarc", "Theme", "name", "default")
    if "atajos" in components:
        shortcuts = json.loads(asset("atajos.json"))
        if not isinstance(shortcuts, list):
            raise ValueError("atajos.json debe contener una lista")
        for item in shortcuts:
            if (not isinstance(item, dict) or set(item) != {"file", "group", "key", "value"}
                    or item["file"] != "kglobalshortcutsrc"
                    or not all(isinstance(v, str) and v and not any(c in v for c in "\n\r\0")
                               for v in item.values())
                    or any(c in item["group"] + item["key"] for c in "[]")):
                raise ValueError("Entrada no válida en atajos.json")
            setting(item["file"], item["group"], item["key"], item["value"])
    if "ventanas" in components:
        for relative in ("metadata.json", "contents/code/main.js"):
            copy("data", SCRIPT + relative, "kwin/eva01-ordenar-ventanas/" + relative)
        copy("data", "applications/eva01-ordenar-ventanas.desktop", "eva01-ordenar-ventanas.desktop")
        setting("kwinrc", "Plugins", "eva01-ordenar-ventanasEnabled", "true")
    if "terminales" in components:
        if not shutil.which("zsh"):
            raise ValueError("Falta zsh; instálelo antes de aplicar el componente terminales.")
        shell = shlex.join(["/usr/bin/env", "ZDOTDIR=" + str(roots["config"] / "plasma-eva01/zsh"),
                            shutil.which("zsh")])
        kitty_path = regular_file(roots["config"] / "kitty/kitty.conf")
        old = kitty_path.read_text() if kitty_path.exists() else ""
        if old.count(KITTY_BEGIN) != old.count(KITTY_END) or old.count(KITTY_BEGIN) > 1:
            raise ValueError("Bloque EVA-01 de Kitty incompleto o duplicado; revíselo antes de instalar.")
        if KITTY_BEGIN in old:
            begin, end = old.index(KITTY_BEGIN), old.index(KITTY_END)
            if end < begin:
                raise ValueError("Bloque EVA-01 de Kitty invertido")
            old = old[:begin] + old[end + len(KITTY_END):].lstrip("\n")
        # El último bloque prevalece sobre la configuración anterior de Kitty.
        copies[("config", "kitty/kitty.conf")] = (
            old.rstrip("\n") + ("\n" if old else "") + KITTY_BEGIN
            + "\ninclude eva01.conf\nshell " + shell + "\n" + KITTY_END + "\n").encode()
        copy("config", "kitty/eva01.conf", "terminales/eva01.conf")
        copy("config", "plasma-eva01/zsh/.zshrc", "terminales/prompt.zsh")
        copy("data", "org.gnome.Ptyxis/palettes/EVA-01.palette", "terminales/EVA-01.palette")
        copy("data", "konsole/EVA-01.colorscheme", "terminales/EVA-01.colorscheme")
        # KConfig se encarga de escapar las rutas, incluidas las que contienen espacios.
        settings.extend([("@profile", "General", "Name", "EVA-01"),
                         ("@profile", "General", "Parent", "FALLBACK/"),
                         ("@profile", "General", "Command", shell),
                         ("@profile", "Appearance", "ColorScheme", "EVA-01")])
        setting("konsolerc", "Desktop Entry", "DefaultProfile", "EVA-01.profile")
    return copies, settings


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_file(path, content, mode=0o644):
    regular_file(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".eva01-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            os.fchmod(stream.fileno(), mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def backup_targets(roots, targets, components):
    directory = safe_path(roots["state"] / "plasma-eva01/backups")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    folder = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-"), dir=directory))
    entries, snapshot = [], []
    for index, (root, name) in enumerate(targets):
        target = regular_file(roots[root] / name)
        entry = {"root": root, "path": name, "existed": target.exists(),
                 "backup": None, "sha256": None, "mode": None}
        data, mode = None, None
        if target.exists():
            data, mode = target.read_bytes(), stat.S_IMODE(target.stat().st_mode)
            if mode & ~0o777:
                raise ValueError(f"Permisos especiales no admitidos: {target}")
            entry.update(backup=f"file-{index:03d}", sha256=digest(data), mode=mode)
            write_file(folder / entry["backup"], data, 0o600)
        entries.append(entry)
        snapshot.append((target, data, mode))
    manifest = {"version": 1, "roots": {k: str(v) for k, v in roots.items()},
                "components": list(components), "entries": entries}
    data = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    write_file(folder / "manifest.json", data, 0o600)
    write_file(folder / "manifest.sha256", digest(data).encode(), 0o600)
    return folder, snapshot


def read_backup(folder, roots):
    safe_path(folder)
    raw = regular_file(folder / "manifest.json").read_bytes()
    expected_hash = regular_file(folder / "manifest.sha256").read_text().strip()
    if digest(raw) != expected_hash:
        raise ValueError("Manifiesto adulterado: checksum no coincide")
    doc = json.loads(raw)
    if (not isinstance(doc, dict) or set(doc) != {"version", "roots", "components", "entries"}
            or doc["version"] != 1 or doc["roots"] != {k: str(v) for k, v in roots.items()}
            or not isinstance(doc["components"], list) or not doc["components"]
            or any(c not in COMPONENTS for c in doc["components"])
            or len(set(doc["components"])) != len(doc["components"])
            or not isinstance(doc["entries"], list)):
        raise ValueError("Manifiesto no válido o pertenece a otras rutas HOME/XDG")
    allowed, seen, snapshot = set(selected_targets(doc["components"])), set(), []
    for index, entry in enumerate(doc["entries"]):
        if (not isinstance(entry, dict)
                or set(entry) != {"root", "path", "existed", "backup", "sha256", "mode"}
                or not isinstance(entry["root"], str) or not isinstance(entry["path"], str)):
            raise ValueError("Entrada de copia no válida")
        key = (entry["root"], entry["path"])
        if key not in allowed or key in seen or type(entry["existed"]) is not bool:
            raise ValueError("Destino no permitido o duplicado en manifiesto")
        seen.add(key)
        target = regular_file(roots[key[0]] / key[1])
        data, mode = None, None
        if entry["existed"]:
            if (entry["backup"] != f"file-{index:03d}" or type(entry["mode"]) is not int
                    or not 0 <= entry["mode"] <= 0o777):
                raise ValueError("Ruta o permisos de copia no válidos")
            data = regular_file(folder / entry["backup"]).read_bytes()
            if digest(data) != entry["sha256"]:
                raise ValueError("Archivo de copia adulterado")
            mode = entry["mode"]
        elif any(entry[k] is not None for k in ("backup", "sha256", "mode")):
            raise ValueError("Estado ausente no válido")
        snapshot.append((target, data, mode))
    if seen != allowed:
        raise ValueError("El manifiesto no contiene todos los destinos de sus componentes")
    return doc["components"], sorted(seen), snapshot


def restore_snapshot(snapshot):
    for target, data, mode in snapshot:
        regular_file(target)
        if data is None:
            target.unlink(missing_ok=True)
        else:
            write_file(target, data, mode)


def apply_plan(roots, copies, settings):
    for (root, name), content in copies.items():
        target = roots[root] / name
        mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
        write_file(target, content, mode)
    for file, group, key, value in settings:
        target = (roots["data"] / "konsole/EVA-01.profile" if file == "@profile"
                  else roots["config"] / file)
        target.parent.mkdir(parents=True, exist_ok=True)
        command = ["kwriteconfig6", "--file", str(target)]
        for subgroup in group.split("]["):
            command.extend(["--group", subgroup])
        run(command + ["--key", key, "--", value])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Aplicar los cambios (por defecto: simulación)")
    parser.add_argument("--components", nargs="+", choices=COMPONENTS, help="Componentes; por defecto todos")
    parser.add_argument("--restore", type=Path, metavar="RUTA_COPIA", help="Restaurar una copia validada")
    parser.add_argument("--no-reload", action="store_true", help="No contactar con la sesión KDE")
    args = parser.parse_args(argv)
    if args.restore and args.components:
        parser.error("--restore y --components son excluyentes")
    roots = roots_from_env()
    if args.restore:
        components, targets, previous = read_backup(args.restore.absolute(), roots)
    else:
        components = list(dict.fromkeys(args.components or COMPONENTS))
        targets = selected_targets(components)
        copies, settings = make_plan(roots, components)
    for root, name in targets:
        regular_file(roots[root] / name)
    print(("APLICAR" if args.apply else "SIMULACIÓN") + ": "
          + ("restaurar " if args.restore else "instalar ") + ", ".join(components))
    for root, name in targets:
        print("  " + str(roots[root] / name))
    if not args.apply:
        print("Sin escrituras. Añada --apply para ejecutar este plan.")
        return 0
    if os.geteuid() == 0:
        raise ValueError("Ejecute como su usuario habitual, sin sudo ni root.")
    if not args.restore and not shutil.which("kwriteconfig6"):
        raise ValueError("Falta kwriteconfig6 (KDE Plasma 6).")
    preflight_reload(args.no_reload)
    folder, rollback = backup_targets(roots, targets, components)
    print("Copia: " + str(folder), flush=True)
    try:
        if args.restore:
            restore_snapshot(previous)
        else:
            apply_plan(roots, copies, settings)
    except (OSError, ValueError, subprocess.SubprocessError):
        restore_snapshot(rollback)
        print("Se ha recuperado el estado previo tras el fallo.", file=sys.stderr)
        raise
    reload_session(components, args.no_reload)
    print("Archivos " + ("restaurados." if args.restore else "preparados.")
          + " Reabra los terminales y cierre/abra la sesión para cargar todos los cambios de apariencia y atajos.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, configparser.Error, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
