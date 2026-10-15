"""Integración aislada: usa kwriteconfig6 real, sin sesión de escritorio."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


INSTALLER = Path(__file__).resolve().parents[1] / "instalar.py"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eva con espacios ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.package = self.base / "paquete"
        self.package.mkdir()
        shutil.copyfile(INSTALLER, self.package / "instalar.py")
        self.home = self.base / "home"
        self.home.mkdir()
        self.config, self.data, self.state = [self.home / p for p in ("config", "data", "state")]
        self.env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.config),
                        XDG_DATA_HOME=str(self.data), XDG_STATE_HOME=str(self.state),
                        QT_QPA_PLATFORM="offscreen")
        self.env.pop("DBUS_SESSION_BUS_ADDRESS", None)
        self.assets = self.package / "assets"
        files = {
            "EVA01Dark.colors": "[General]\nName=EVA\n[Colors:Window]\nBackgroundNormal=18,20,24\nForegroundNormal=235,235,235\n[Colors:Header][Inactive]\nBackgroundNormal=35,40,45\n[WM]\nactiveBackground=123,40,160\n",
            "kwin/eva01-ordenar-ventanas/metadata.json": '{"KPlugin":{"Id":"eva01-ordenar-ventanas"}}',
            "kwin/eva01-ordenar-ventanas/contents/code/main.js": "// ejemplo\n",
            "eva01-ordenar-ventanas.desktop": "[Desktop Entry]\nName=EVA\nType=Application\nExec=qdbus6\n",
            "terminales/eva01.conf": "foreground #e0e0e0\nbackground #101010\n",
            "terminales/EVA-01.colorscheme": "[General]\nDescription=EVA-01\n",
            "terminales/EVA-01.palette": "#101010:#eeeeee\n",
            "terminales/prompt.zsh": "export HISTFILE=$ZDOTDIR/history\nPROMPT='EVA> '\n",
            "atajos.json": json.dumps([{"file":"kglobalshortcutsrc", "group":"org.kde.krunner.desktop", "key":"_launch", "value":"Alt+Space,Alt+Space,KRunner"}]),
        }
        for name, content in files.items():
            path = self.assets / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def run_installer(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(self.package / "instalar.py"), *args],
                                env=self.env, capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def write(self, name, content):
        path = self.config / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def snapshot(self):
        return {str(p.relative_to(self.home)): (p.read_bytes(), p.stat().st_mode & 0o777)
                for p in self.home.rglob("*") if p.is_file() and self.state not in p.parents}

    def backup(self):
        return sorted((self.state / "plasma-eva01/backups").iterdir())[-1]

    def alter_manifest(self, directory, change):
        path = directory / "manifest.json"
        manifest = json.loads(path.read_text())
        change(manifest)
        path.write_text(json.dumps(manifest))
        (directory / "manifest.sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest())

    def test_dry_run_creates_nothing(self):
        before = set(self.home.rglob("*"))
        result = self.run_installer()
        self.assertIn("SIMULACIÓN", result.stdout)
        self.assertEqual(set(self.home.rglob("*")), before)

    def test_component_preserves_panel_and_unrelated_keys(self):
        panel = self.write("plasma-org.kde.plasma.desktop-appletsrc", b"panel intacto\n")
        self.write("kdeglobals", b"[General]\nOther=conservar\n")
        self.run_installer("--apply", "--components", "apariencia", "--no-reload")
        self.assertEqual(panel.read_bytes(), b"panel intacto\n")
        self.assertIn("Other=conservar", (self.config / "kdeglobals").read_text())
        self.assertIn("ColorScheme=EVA01Dark", (self.config / "kdeglobals").read_text())
        self.assertFalse((self.config / "kwinrc").exists())
        self.assertFalse((self.config / "kitty").exists())

    def test_appearance_writes_nested_kconfig_groups(self):
        self.run_installer("--apply", "--components", "apariencia", "--no-reload")
        result = subprocess.run(["kreadconfig6", "--file", str(self.config / "kdeglobals"),
                                 "--group", "Colors:Header", "--group", "Inactive",
                                 "--key", "BackgroundNormal"], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "35,40,45")

    def test_ptyxis_palette_is_in_application_palette_directory(self):
        self.run_installer("--apply", "--components", "terminales", "--no-reload")
        self.assertEqual((self.data / "org.gnome.Ptyxis/palettes/EVA-01.palette").read_bytes(),
                         (self.assets / "terminales/EVA-01.palette").read_bytes())

    def test_apply_repeat_restore_exact_bytes_and_leave_unrelated_files(self):
        originals = {"kdeglobals": b"# mi comentario\n[General]\nColorScheme=Otro\n",
                     "kitty/kitty.conf": b"font_size 12\nshell /bin/bash\n",
                     "konsolerc": b"[Desktop Entry]\nDefaultProfile=Otro.profile\n"}
        for name, content in originals.items():
            self.write(name, content)
        (self.config / "kdeglobals").chmod(0o640)
        self.write("plasma-org.kde.plasma.desktop-appletsrc", b"panel original\n")
        initial = self.snapshot()
        self.run_installer("--apply", "--no-reload")
        backup = self.backup()
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        installed = self.snapshot()
        kitty = (self.config / "kitty/kitty.conf").read_text()
        self.assertIn("shell /bin/bash", kitty)
        self.assertIn("ZDOTDIR=", kitty)
        self.run_installer("--apply", "--no-reload")
        self.assertEqual(self.snapshot(), installed)
        unrelated = self.config / "kitty/personales.txt"
        unrelated.write_text("conservar")
        self.run_installer("--restore", str(backup), "--apply", "--no-reload")
        self.assertEqual(unrelated.read_text(), "conservar")
        restored = self.snapshot()
        restored.pop(str(unrelated.relative_to(self.home)))
        self.assertEqual(restored, initial)

    def test_target_symlink_rejected_before_any_write(self):
        outside = self.base / "original"
        outside.write_text("intacto")
        self.config.mkdir()
        (self.config / "kdeglobals").symlink_to(outside)
        self.run_installer("--apply", "--no-reload", ok=False)
        self.assertEqual(outside.read_text(), "intacto")
        self.assertFalse(self.state.exists())

    def test_obstructed_parent_rejected_before_backup_or_writes(self):
        self.write("kdeglobals", b"[General]\nColorScheme=Anterior\n")
        self.write("kitty", b"archivo que obstruye el directorio\n")
        before = self.snapshot()
        self.run_installer("--apply", "--no-reload", ok=False)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.state.exists())

    def test_restore_rejects_traversal_even_with_recomputed_checksum(self):
        self.run_installer("--apply", "--components", "apariencia", "--no-reload")
        backup = self.backup()
        before = self.snapshot()
        self.alter_manifest(backup, lambda doc: doc["entries"][0].update(path="../fuera"))
        self.run_installer("--restore", str(backup), "--apply", "--no-reload", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_restore_rejects_corrupt_backup_before_writes(self):
        self.write("kdeglobals", b"[General]\nOther=test\n")
        self.run_installer("--apply", "--components", "apariencia", "--no-reload")
        backup = self.backup()
        manifest = json.loads((backup / "manifest.json").read_text())
        saved = next(e for e in manifest["entries"] if e["existed"])
        (backup / saved["backup"]).write_bytes(b"adulterado")
        before = self.snapshot()
        self.run_installer("--restore", str(backup), "--apply", "--no-reload", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_reload_preflight_without_session_does_not_write(self):
        self.run_installer("--apply", ok=False)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_partial_write_failure_restores_previous_bytes(self):
        self.write("kdeglobals", b"[General]\nColorScheme=Anterior\n")
        self.write("kitty/kitty.conf", b"# conservar\n")
        before = self.snapshot()
        commands = self.base / "commands"
        commands.mkdir()
        wrapper = commands / "kwriteconfig6"
        wrapper.write_text('#!/bin/sh\ncase "$*" in *ColorScheme*) exit 23;; esac\nexec /usr/bin/kwriteconfig6 "$@"\n')
        wrapper.chmod(0o755)
        self.env["PATH"] = str(commands) + os.pathsep + self.env["PATH"]
        result = self.run_installer("--apply", "--no-reload", ok=False)
        self.assertIn("recuperado el estado previo", result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue((self.backup() / "manifest.json").exists())

    def test_restore_rejects_foreign_xdg_roots_and_symlink_payloads(self):
        self.write("kdeglobals", b"[General]\nOther=test\n")
        self.run_installer("--apply", "--components", "apariencia", "--no-reload")
        backup = self.backup()
        before = self.snapshot()
        original_config = self.env["XDG_CONFIG_HOME"]
        self.env["XDG_CONFIG_HOME"] = str(self.home / "otro-config")
        self.run_installer("--restore", str(backup), "--apply", "--no-reload", ok=False)
        self.assertFalse((self.home / "otro-config").exists())
        self.env["XDG_CONFIG_HOME"] = original_config
        manifest = json.loads((backup / "manifest.json").read_text())
        saved = next(e for e in manifest["entries"] if e["existed"])
        payload = backup / saved["backup"]
        outside = self.base / "payload-original"
        payload.rename(outside)
        payload.symlink_to(outside)
        self.run_installer("--restore", str(backup), "--apply", "--no-reload", ok=False)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
