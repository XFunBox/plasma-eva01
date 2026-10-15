"""Instalación de archivos real en XDG temporal; no modifica la sesión Plasma."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
PLUGIN = "com.xfunbox.nervdeck"


class WidgetInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nerv con espacios ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.package = self.base / "package"
        self.package.mkdir()
        for name in ("instalar-widget.py", "instalar.py"):
            shutil.copyfile(REPO / name, self.package / name)
        self.source = self.package / "widget"
        (self.source / "contents/ui").mkdir(parents=True)
        (self.source / "metadata.json").write_text(json.dumps({"KPlugin": {"Id": PLUGIN}}))
        (self.source / "contents/ui/main.qml").write_text("import QtQuick\nItem {}\n")
        for path in self.source.rglob("*"):
            path.chmod(0o755 if path.is_dir() else 0o644)
        self.home = self.base / "home"
        self.home.mkdir()
        self.data, self.state = self.home / "data", self.home / "state"
        self.config = self.home / "config"
        self.config.mkdir()
        self.panel = self.config / "plasma-org.kde.plasma.desktop-appletsrc"
        self.panel.write_bytes(b"panel intacto\n")
        self.env = dict(os.environ, HOME=str(self.home), XDG_DATA_HOME=str(self.data),
                        XDG_STATE_HOME=str(self.state), XDG_CONFIG_HOME=str(self.config))
        self.target = self.data / "plasma/plasmoids" / PLUGIN

    def run_install(self, *args, ok=True, env=None):
        result = subprocess.run([sys.executable, str(self.package / "instalar-widget.py"), *args],
                                env=env or self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def backup(self):
        return sorted((self.state / "nerv-deck/backups").iterdir())[-1]

    def snapshot(self, path):
        return {str(p.relative_to(path)): (p.read_bytes(), p.stat().st_mode & 0o777)
                for p in path.rglob("*") if p.is_file()}

    def test_dry_run_does_not_write(self):
        before = set(self.base.rglob("*"))
        self.assertIn("SIMULACIÓN", self.run_install().stdout)
        self.assertEqual(before, set(self.base.rglob("*")))

    def test_install_overwrite_and_restore_exact_package(self):
        self.target.mkdir(parents=True)
        (self.target / "metadata.json").write_bytes((self.source / "metadata.json").read_bytes())
        old = self.target / "personal.txt"
        old.write_bytes("versión anterior\n".encode())
        old.chmod(0o640)
        (self.target / "vacio").mkdir()
        sibling = self.target.parent / "otro-widget"
        sibling.mkdir()
        (sibling / "personal").write_text("conservar")
        initial = self.snapshot(self.target)
        self.run_install("--apply")
        backup = self.backup()
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.snapshot(self.target), self.snapshot(self.source))
        self.run_install("--restore", str(backup), "--apply")
        self.assertEqual(self.snapshot(self.target), initial)
        self.assertTrue((self.target / "vacio").is_dir())
        self.assertEqual((sibling / "personal").read_text(), "conservar")
        self.assertEqual(self.panel.read_bytes(), b"panel intacto\n")

    def test_restore_absent_package_removes_only_plugin(self):
        self.run_install("--apply")
        backup = self.backup()
        self.run_install("--restore", str(backup))
        self.assertTrue(self.target.is_dir())
        self.run_install("--restore", str(backup), "--apply")
        self.assertFalse(self.target.exists())
        self.assertEqual(self.panel.read_bytes(), b"panel intacto\n")

    def test_symlink_destination_rejected_before_write(self):
        outside = self.base / "outside"
        outside.mkdir()
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(outside, target_is_directory=True)
        self.run_install("--apply", ok=False)
        self.assertFalse(self.state.exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_restore_rejects_other_roots_and_tampered_manifest(self):
        self.run_install("--apply")
        backup = self.backup()
        installed = self.snapshot(self.target)
        env = dict(self.env, XDG_DATA_HOME=str(self.home / "other-data"))
        self.run_install("--restore", str(backup), "--apply", env=env, ok=False)
        manifest = backup / "manifest.json"
        doc = json.loads(manifest.read_text())
        doc["plugin"] = "otro-widget"
        manifest.write_text(json.dumps(doc))
        (backup / "manifest.sha256").write_text(hashlib.sha256(manifest.read_bytes()).hexdigest())
        self.run_install("--restore", str(backup), "--apply", ok=False)
        self.assertEqual(self.snapshot(self.target), installed)

    def test_rejects_symlink_inside_source_and_other_plugin_destination(self):
        (self.source / "enlace").symlink_to(self.panel)
        self.run_install("--apply", ok=False)
        self.assertFalse(self.state.exists())
        (self.source / "enlace").unlink()
        self.target.mkdir(parents=True)
        (self.target / "metadata.json").write_text('{"KPlugin":{"Id":"otro-widget"}}')
        self.run_install("--apply", ok=False)
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
