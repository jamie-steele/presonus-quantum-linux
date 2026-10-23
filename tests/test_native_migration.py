import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cleanup = load("cleanup_state", ROOT / "scripts/maintenance/cleanup-ubuntu.py")
with patch.dict(sys.modules, {"cleanup_state": cleanup}):
    migration = load("native_migration", ROOT / "packaging/native/migrate_legacy.py")
native = load("native_builder_migration", ROOT / "scripts/release/build_native.py")
TARGET = "20260820.rfc1.s1148921-3"
OLD = "20260820.rfc1.s1148921"


class NativeMigrationTests(unittest.TestCase):
    def write(self, root, name, content="fixture\n"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def assets(self, root):
        assets = root / "assets"
        old = (ROOT / "driver/modprobe.d/quantum2626-inhouse.conf").read_bytes()
        self.write(assets, "migration-identities.json", json.dumps({
            "inhouse_policy_sha256": hashlib.sha256(old).hexdigest(),
        }))
        self.write(assets, "backend-upstream.conf", "blacklist snd-quantum2626\n")
        return assets, old

    def test_migration_only_retires_older_release_versions(self):
        for candidate, expected in ((OLD, True), (OLD + "-2", True), (TARGET, False),
                                    (OLD + "-4", False), ("20260701.rfc1.s12345", True),
                                    ("20261001.rfc2.s12345", False),
                                    ("unrecognized", False)):
            with self.subTest(candidate=candidate):
                self.assertEqual(migration.older_release(candidate, TARGET), expected)

    def test_removal_backs_up_module_source_and_generated_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets, policy_bytes = self.assets(root)
            module = self.write(root, "lib/modules/test/extra/snd-quantum2626.ko")
            source = self.write(root, f"usr/src/quantum-{OLD}/dkms.conf").parent
            policy = self.write(root, "etc/modprobe.d/quantum2626-backend.conf", policy_bytes.decode())
            plan = {"files": [str(module)], "sources": [str(source)], "dkms_versions": [OLD, TARGET], "review": []}
            empty = {"files": [], "sources": [], "dkms_versions": [TARGET], "review": []}
            restored = root / "lib/modules/test/extra/snd-quantum.ko"
            after_removal = dict(plan, files=[str(module), str(restored)])
            def command(arguments, **kwargs):
                if arguments[:2] == ["dkms", "remove"]:
                    self.assertEqual((next((root / "var/backups/quantum-migration").iterdir()) / "files" / module.relative_to(root)).read_text(), "fixture\n")
                    restored.write_text("DKMS restored original module\n")
                return subprocess.CompletedProcess(arguments, 0, "", "")
            with patch.object(cleanup, "discover", side_effect=[plan, after_removal, empty]), \
                    patch.object(cleanup, "owners", return_value=[]), \
                    patch.object(cleanup, "command", side_effect=command):
                backup = migration.migrate(TARGET, root, assets)
            self.assertFalse(module.exists())
            self.assertFalse(restored.exists())
            self.assertEqual((backup / "files" / restored.relative_to(root)).read_text(),
                             "DKMS restored original module\n")
            self.assertFalse(source.exists())
            self.assertEqual(policy.read_text(), "blacklist snd-quantum2626\n")
            self.assertEqual((backup / "files" / policy.relative_to(root)).read_bytes(), policy_bytes)

    def test_custom_policy_and_other_package_policy_are_preserved(self):
        for customized in (False, True):
            with self.subTest(customized=customized), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                assets, original = self.assets(root)
                text = original.decode() + ("# local customization\n" if customized else "")
                policy = self.write(root, "etc/modprobe.d/quantum2626-backend.conf", text)
                empty = {"files": [], "sources": [], "dkms_versions": [], "review": []}
                ownership = [] if customized else ["different-package"]
                with patch.object(cleanup, "discover", return_value=empty), \
                        patch.object(cleanup, "owners", return_value=ownership):
                    self.assertIsNone(migration.migrate(TARGET, root, assets))
                self.assertEqual(policy.read_text(), text)

    def test_failed_backup_does_not_remove_legacy_registration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets, _ = self.assets(root)
            module = self.write(root, "lib/modules/test/extra/snd-quantum2626.ko")
            plan = {"files": [str(module)], "sources": [], "dkms_versions": [OLD], "review": []}
            with patch.object(cleanup, "discover", return_value=plan), \
                    patch.object(cleanup, "command") as command, \
                    patch.object(migration, "older_release", return_value=True), \
                    patch.object(migration.shutil, "copy2", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    migration.migrate(TARGET, root, assets)
                command.assert_not_called()
            self.assertTrue(module.exists())

    def test_every_target_build_precedes_migration_and_install(self):
        script = native.lifecycle(TARGET, "configure_module", migration=True)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for kernel in ("kernel-a", "kernel-b"):
                self.write(root, f"modules/{kernel}/build/Makefile")
            log = root / "calls"
            executables = root / "bin"
            for name in ("dkms", "depmod", "python3"):
                path = self.write(executables, name, f'#!/bin/sh\nprintf "{name} %s\\n" "$*" >> "{log}"\n')
                path.chmod(0o755)
            script = script.replace("/lib/modules/", str(root / "modules") + "/")
            script = script.replace("/boot/", str(root / "boot") + "/")
            result = subprocess.run(["sh"], input=script, text=True, capture_output=True,
                                    env=dict(os.environ, PATH=f"{executables}:/usr/bin:/bin"))
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = log.read_text().splitlines()
            migration_index = next(index for index, call in enumerate(calls) if call.startswith("python3 "))
            builds = [index for index, call in enumerate(calls) if call.startswith("dkms build ")]
            installs = [index for index, call in enumerate(calls) if call.startswith("dkms install ")]
            self.assertEqual(len(builds), 2)
            self.assertTrue(all(index < migration_index for index in builds))
            self.assertTrue(all(index > migration_index for index in installs))
            # A migration failure must leave installation pending, never proceed
            # to force-install or report success after a partial retirement.
            log.unlink()
            (executables / "python3").write_text("#!/bin/sh\nexit 9\n")
            failed = subprocess.run(["sh"], input=script, text=True, capture_output=True,
                                    env=dict(os.environ, PATH=f"{executables}:/usr/bin:/bin"))
            self.assertEqual(failed.returncode, 9)
            self.assertNotIn("dkms install", log.read_text())
            self.assertNotIn("Quantum installed", failed.stdout)

    def test_preinst_rejects_symlink_before_removing_generated_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = (ROOT / "driver/modprobe.d/quantum2626-inhouse.conf").read_bytes()
            policy = self.write(root, "etc/modprobe.d/quantum2626-backend.conf", original.decode())
            self.write(root, "usr/share/alsa/ucm2/P2626/P2626.conf")
            unrelated = self.write(root, "unrelated-profile", "unrelated content\n")
            (root / "usr/share/alsa/ucm2/P2626/HiFi.conf").symlink_to(unrelated)
            script = (ROOT / "packaging/native/preinst.sh").read_text()
            for prefix in ("/usr/share/", "/etc/", "/var/backups/"):
                script = script.replace(prefix, str(root) + prefix)
            script = script.replace("@INHOUSE_SHA256@", hashlib.sha256(original).hexdigest())
            result = subprocess.run(["sh", "-s", "--", "install"], input=script,
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("non-regular profile", result.stderr)
            self.assertEqual(policy.read_bytes(), original)
            self.assertEqual(unrelated.read_text(), "unrelated content\n")

    def test_preinst_is_posix_shell_and_independent_of_python(self):
        text = (ROOT / "packaging/native/preinst.sh").read_text()
        subprocess.run(["sh", "-n"], input=text, text=True, check=True)
        self.assertNotIn("python3", text)
        for command in ("modprobe", "rmmod", "systemctl", "service"):
            self.assertNotRegex(text, rf"(?m)^\s*{command}\s")


if __name__ == "__main__":
    unittest.main()
