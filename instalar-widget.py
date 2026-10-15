#!/usr/bin/env python3
"""Instala NERV Deck por usuario; sin --apply sólo comprueba y muestra el plan."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile

# La simulación tampoco crea bytecode junto al instalador.
sys.dont_write_bytecode = True

from instalar import digest, regular_file, roots_from_env, safe_path, write_file

PLUGIN = "com.xfunbox.nervdeck"
SOURCE = Path(__file__).resolve().parent / "widget"


def plugin_tree(path):
    """Inventario completo de un único paquete, sin enlaces ni archivos especiales."""
    safe_path(path)
    if not path.is_dir():
        raise ValueError(f"Se esperaba un paquete: {path}")
    metadata = json.loads(regular_file(path / "metadata.json").read_text())
    if not isinstance(metadata, dict) or not isinstance(metadata.get("KPlugin"), dict) or metadata["KPlugin"].get("Id") != PLUGIN:
        raise ValueError(f"El paquete no pertenece a {PLUGIN}: {path}")
    entries = []
    for item in [path, *sorted(path.rglob("*"))]:
        safe_path(item)
        info = item.stat()
        mode = stat.S_IMODE(info.st_mode)
        if mode & ~0o777:
            raise ValueError(f"Permisos especiales no admitidos: {item}")
        entry = {"path": str(item.relative_to(path)), "mode": mode}
        if stat.S_ISDIR(info.st_mode):
            entry["kind"] = "directory"
        elif stat.S_ISREG(info.st_mode):
            entry.update(kind="file", sha256=digest(item.read_bytes()))
        else:
            raise ValueError(f"No se admiten archivos especiales: {item}")
        entries.append(entry)
    return entries


def backup_root(roots):
    return safe_path(roots["state"] / "nerv-deck/backups")


def make_backup(roots, target, previous):
    directory = backup_root(roots)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    folder = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-"), dir=directory))
    if previous is not None:
        shutil.copytree(target, folder / "package")
        if plugin_tree(folder / "package") != previous:
            raise ValueError("El paquete cambió mientras se preparaba la copia; no se ha sustituido")
    manifest = {"version": 1, "plugin": PLUGIN,
                "roots": {name: str(roots[name]) for name in ("data", "state")},
                "existed": previous is not None, "tree": previous}
    raw = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    write_file(folder / "manifest.json", raw, 0o600)
    write_file(folder / "manifest.sha256", digest(raw).encode(), 0o600)
    return folder


def read_backup(folder, roots):
    safe_path(folder)
    if folder.parent != backup_root(roots) or not folder.is_dir():
        raise ValueError("La copia debe pertenecer a las mismas rutas XDG de NERV Deck")
    raw = regular_file(folder / "manifest.json").read_bytes()
    if digest(raw) != regular_file(folder / "manifest.sha256").read_text().strip():
        raise ValueError("Manifiesto alterado: checksum incorrecto")
    manifest = json.loads(raw)
    if (not isinstance(manifest, dict)
            or set(manifest) != {"version", "plugin", "roots", "existed", "tree"}
            or type(manifest["version"]) is not int or manifest["version"] != 1
            or manifest["plugin"] != PLUGIN
            or manifest["roots"] != {name: str(roots[name]) for name in ("data", "state")}
            or type(manifest["existed"]) is not bool):
        raise ValueError("Manifiesto no válido o pertenece a otras rutas XDG")
    if manifest["existed"]:
        if not isinstance(manifest["tree"], list) or plugin_tree(folder / "package") != manifest["tree"]:
            raise ValueError("El contenido de la copia no coincide con su manifiesto")
        return folder / "package"
    if manifest["tree"] is not None or (folder / "package").exists() or (folder / "package").is_symlink():
        raise ValueError("La copia de un paquete ausente no debe contener archivos")
    return None


def replace_package(roots, target, source, previous, normalise=False):
    """Prepara todo antes de sustituir el directorio y conserva una copia reversible."""
    target.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".nervdeck-", dir=target.parent))
    stage, displaced = work / "package", work / "previous"
    try:
        if source is not None:
            shutil.copytree(source, stage)
            if normalise:
                for item in [stage, *stage.rglob("*")]:
                    item.chmod(0o755 if item.is_dir() else 0o644)
            plugin_tree(stage)
        # El destino se revalida antes de tocarlo, también en restauraciones.
        current = plugin_tree(target) if target.exists() else None
        if current != previous:
            raise ValueError("El paquete cambió durante la preparación; vuelva a intentarlo")
        backup = make_backup(roots, target, previous)
        if previous is not None:
            target.rename(displaced)
        try:
            if source is not None:
                stage.rename(target)
        except OSError:
            if displaced.exists():
                displaced.rename(target)
            raise
        return backup
    finally:
        # work es un directorio temporal propio, nunca una ruta del manifiesto.
        shutil.rmtree(work)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Aplicar el plan (sin esta opción no se escribe nada)")
    parser.add_argument("--restore", type=Path, metavar="COPIA", help="Restaurar una copia de este usuario y estas rutas XDG")
    args = parser.parse_args(argv)
    roots = roots_from_env()
    target = safe_path(roots["data"] / "plasma/plasmoids" / PLUGIN)
    safe_path(backup_root(roots))
    previous = plugin_tree(target) if target.exists() else None
    if args.restore is not None:
        source = read_backup(args.restore, roots)
        action = "Restaurar" if source else "Retirar"
    else:
        source = SOURCE
        plugin_tree(source)
        if not regular_file(source / "contents/ui/main.qml").is_file():
            raise ValueError("El paquete está incompleto: falta contents/ui/main.qml")
        action = "Instalar"
    print(f"{'APLICAR' if args.apply else 'SIMULACIÓN'}: {action} {PLUGIN}\nDestino: {target}")
    if args.apply:
        if os.geteuid() == 0:
            raise ValueError("Ejecute con su usuario habitual, sin sudo ni root.")
        backup = replace_package(roots, target, source, previous, normalise=args.restore is None)
        print(f"Copia previa: {backup}")
        print("Restauración completada." if args.restore else
              "Archivos preparados. Añade NERV Deck desde el selector de widgets de Plasma.")
    else:
        print("No se ha escrito ningún archivo. Usa --apply para aplicar el plan.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
