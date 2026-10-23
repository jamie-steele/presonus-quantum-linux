import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cleanup", ROOT / "scripts/maintenance/cleanup-ubuntu.py")
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class CleanupTests(unittest.TestCase):
    def write(self, root, relative, text="Quantum fixture\n"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def discover(self, root, **kwargs):
        with patch.object(cleanup, "command", return_value=subprocess.CompletedProcess([], 1, "", "")), \
                patch.object(cleanup.shutil, "which", return_value=None), \
                patch.object(cleanup, "owners", return_value=[]):
            return cleanup.discover(root, **kwargs)

    def test_preview_recognizes_both_backends_without_touching_unrelated_modules(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = self.write(root, "lib/modules/test/extra/snd-quantum2626.ko.xz")
            new = self.write(root, "lib/modules/test/updates/dkms/snd-quantum.ko.zst")
            unrelated = self.write(root, "lib/modules/test/extra/another.ko")
            builtin = self.write(root, "lib/modules/test/kernel/sound/snd-quantum.ko")
            plan = self.discover(root)
            self.assertEqual(set(plan["files"]), {str(old), str(new)})
            for path in (old, new, unrelated, builtin):
                self.assertTrue(path.exists())

    def test_symlink_candidates_and_parents_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = self.write(root, "unrelated/HiFi.conf")
            directory = root / "usr/share/alsa/ucm2/P2626"
            directory.parent.mkdir(parents=True)
            directory.symlink_to(outside.parent)
            plan = self.discover(root)
            self.assertEqual(plan["files"], [])
            self.assertTrue(plan["review"])
            self.assertTrue(outside.exists())

    def test_staged_absolute_merged_usr_alias_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "lib").symlink_to("/usr/lib")
            self.assertFalse(cleanup.safe_path(root, root / "lib/modules"))

    def test_custom_shared_configuration_is_reported_and_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write(root, "etc/modprobe.d/my-audio.conf", "options snd-quantum foo=1\noptions unrelated bar=2\n")
            plan = self.discover(root)
            self.assertNotIn(str(path), plan["files"])
            self.assertIn(str(path), "\n".join(plan["review"]))
            asound = self.write(root, "home/tester/.asoundrc", "pcm.!default { card P2626 }\n")
            custom = self.write(root, "home/tester/.config/pipewire/pipewire.conf.d/custom.conf", "# quantum setting\n")
            plan = self.discover(root, user_home=root / "home/tester")
            for preserved in (asound, custom):
                self.assertNotIn(str(preserved), plan["files"])
                self.assertIn(str(preserved), "\n".join(plan["review"]))

    def test_apt_configuration_requires_explicit_option_and_standard_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.write(root, "etc/apt/sources.list.d/quantum.sources", "Types: deb\nURIs: https://jamie-steele.github.io/presonus-quantum-linux\n")
            key = self.write(root, "etc/apt/keyrings/quantum-archive-keyring.gpg")
            self.assertNotIn(str(source), self.discover(root)["files"])
            self.assertEqual(set(self.discover(root, remove_apt=True)["files"]), {str(source), str(key)})
            source.write_text(source.read_text() + "Types: deb\nURIs: https://another.invalid\n")
            self.assertEqual(self.discover(root, remove_apt=True)["files"], [])

    def test_source_tree_requires_exact_dkms_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version = "20260820.rfc1.s1148921"
            config = self.write(root, f"usr/src/quantum-{version}/dkms.conf", f'PACKAGE_NAME="quantum"\nPACKAGE_VERSION="{version}"\n')
            self.assertEqual(self.discover(root)["sources"], [str(config.parent)])
            config.write_text('PACKAGE_NAME="unrelated"\n')
            self.assertEqual(self.discover(root)["sources"], [])

    def test_merged_usr_alias_does_not_hide_package_ownership(self):
        with patch.object(cleanup, "command", side_effect=[
            subprocess.CompletedProcess([], 1, "", ""),
            subprocess.CompletedProcess([], 0, "distro-driver: /usr/lib/modules/test/extra/snd-quantum.ko\n", ""),
        ]) as query:
            self.assertEqual(cleanup.owners(Path("/lib/modules/test/extra/snd-quantum.ko")), ["distro-driver"])
            self.assertEqual(query.call_args.args[0][-1], "/usr/lib/modules/test/extra/snd-quantum.ko")

    def test_other_package_ownership_prevents_removal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.write(root, cleanup.PROFILE_PATHS[0])
            with patch.object(cleanup, "command", return_value=subprocess.CompletedProcess([], 1, "", "")), \
                    patch.object(cleanup.shutil, "which", return_value=None), \
                    patch.object(cleanup, "owners", return_value=["alsa-ucm-conf"]):
                plan = cleanup.discover(root)
            self.assertNotIn(str(path), plan["files"])
            self.assertIn("alsa-ucm-conf", "\n".join(plan["review"]))

    def test_backup_precedes_removal_and_repeat_apply_is_empty(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "etc/os-release", "ID=ubuntu\n")
            profile = self.write(root, cleanup.PROFILE_PATHS[1], "custom profile\n")
            plan = self.discover(root)
            with patch.object(cleanup.os, "geteuid", return_value=0), \
                    patch.object(cleanup, "owners", return_value=[]), \
                    patch.object(cleanup, "discover", return_value=self.discover(root / "empty")):
                backup = cleanup.apply(plan, root)
            self.assertFalse(profile.exists())
            self.assertEqual((backup / "files" / profile.relative_to(root)).read_text(), "custom profile\n")
            self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
            empty = self.discover(root)
            with patch.object(cleanup.os, "geteuid", return_value=0):
                self.assertIsNone(cleanup.apply(empty, root))

    def test_failed_backup_leaves_original_files_intact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "etc/os-release", "ID=ubuntu\n")
            path = self.write(root, cleanup.PROFILE_PATHS[1])
            plan = self.discover(root)
            with patch.object(cleanup.os, "geteuid", return_value=0), \
                    patch.object(cleanup.shutil, "copy2", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    cleanup.apply(plan, root)
            self.assertTrue(path.exists())

    def test_failed_package_purge_stops_manual_deletion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "etc/os-release", "ID=ubuntu\n")
            path = self.write(root, cleanup.PROFILE_PATHS[1])
            plan = self.discover(root)
            plan["package"] = True
            with patch.object(cleanup.os, "geteuid", return_value=0), \
                    patch.object(cleanup, "command", side_effect=[
                        subprocess.CompletedProcess([], 0, str(path) + "\n", ""),
                        RuntimeError("dependency prevents purge"),
                    ]):
                with self.assertRaisesRegex(RuntimeError, "dependency prevents purge"):
                    cleanup.apply(plan, root)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
