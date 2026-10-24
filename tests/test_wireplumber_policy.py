import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
specification = importlib.util.spec_from_file_location(
    "wireplumber_policy", ROOT / "packaging/native/wireplumber_policy.py",
)
policy = importlib.util.module_from_spec(specification)
specification.loader.exec_module(policy)


class WirePlumberPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.assets = self.root / "usr/share/quantum-dkms/wireplumber"
        self.assets.mkdir(parents=True)
        for _, name in policy.POLICIES.values():
            (self.assets / name).write_bytes((ROOT / "alsa/wireplumber" / name).read_bytes())

    def destination(self, series):
        directory, name = policy.POLICIES[series]
        return self.root / "usr/share/wireplumber" / directory / name

    def test_selects_only_matching_policy_and_handles_both_generation_transitions(self):
        for series in ("0.4", "0.4", "0.5", "0.5", "0.4"):
            with self.subTest(series=series):
                policy.select_policy(self.root, series)
                selected = self.destination(series)
                self.assertTrue(selected.is_symlink())
                self.assertEqual(selected.readlink(),
                                 Path("/usr/share/quantum-dkms/wireplumber") / selected.name)
                other = self.destination("0.5" if series == "0.4" else "0.4")
                self.assertFalse(other.is_symlink())
                self.assertFalse(other.exists())

    def test_migrates_exact_legacy_files_and_removes_obsolete_lua(self):
        for series in policy.POLICIES:
            destination = self.destination(series)
            destination.parent.mkdir(parents=True)
            destination.write_bytes((self.assets / destination.name).read_bytes())
        policy.select_policy(self.root, "0.5")
        self.assertFalse(self.destination("0.4").exists())
        self.assertTrue(self.destination("0.5").is_symlink())

    def test_custom_inactive_rule_blocks_switch_without_modifying_either_path(self):
        policy.select_policy(self.root, "0.4")
        custom = self.destination("0.5")
        custom.parent.mkdir(parents=True)
        custom.write_text("custom policy\n")
        with self.assertRaisesRegex(ValueError, "Preserved customized"):
            policy.select_policy(self.root, "0.5")
        self.assertEqual(custom.read_text(), "custom policy\n")
        self.assertTrue(self.destination("0.4").is_symlink())

    def test_unexpected_symlink_is_preserved(self):
        destination = self.destination("0.4")
        destination.parent.mkdir(parents=True)
        destination.symlink_to("/unrelated/policy.lua")
        with self.assertRaisesRegex(ValueError, "unexpected policy symlink"):
            policy.select_policy(self.root, "0.5")
        self.assertEqual(destination.readlink(), Path("/unrelated/policy.lua"))
        self.assertFalse(self.destination("0.5").is_symlink())

    def test_symlink_parent_is_rejected_without_writing_outside_root(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "usr/share/wireplumber").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlink directory"):
            policy.select_policy(self.root, "0.5")
        self.assertEqual(list(outside.iterdir()), [])

    def test_removal_deletes_only_managed_links_and_does_not_need_assets_or_version(self):
        policy.select_policy(self.root, "0.5")
        for source in self.assets.iterdir():
            source.unlink()
        custom = self.destination("0.4")
        custom.parent.mkdir(parents=True)
        custom.write_text("custom policy\n")
        policy.select_policy(self.root, remove=True)
        policy.select_policy(self.root, remove=True)
        self.assertFalse(self.destination("0.5").is_symlink())
        self.assertEqual(custom.read_text(), "custom policy\n")

    def test_missing_template_and_unknown_series_do_not_change_current_selection(self):
        policy.select_policy(self.root, "0.4")
        (self.assets / self.destination("0.5").name).unlink()
        for series in ("0.5", "unknown"):
            with self.subTest(series=series), self.assertRaises(ValueError):
                policy.select_policy(self.root, series)
            self.assertTrue(self.destination("0.4").is_symlink())

    def test_detects_supported_versions_without_connecting_to_audio(self):
        for version, expected in (("wireplumber\nCompiled with libwireplumber 0.4.17\n", "0.4"),
                                  ("wireplumber 0.5.12\n", "0.5"),
                                  ("wireplumber 0.10.0\n", "0.5")):
            with self.subTest(version=version), patch.object(policy.subprocess, "run") as command:
                command.return_value = subprocess.CompletedProcess([], 0, version, "")
                self.assertEqual(policy.installed_series(), expected)
                self.assertEqual(command.call_args.args[0], ["wireplumber", "--version"])

    def test_jammy_version_fallback_and_unsupported_versions(self):
        with patch.object(policy.subprocess, "run") as command:
            command.side_effect = [
                subprocess.CompletedProcess([], 1, "", "unknown option"),
                subprocess.CompletedProcess([], 0, "1:0.4.8-4ubuntu2", ""),
            ]
            self.assertEqual(policy.installed_series(), "0.4")
            self.assertEqual(command.call_args.args[0][0], "dpkg-query")
        for version in ("wireplumber 0.3.1", "unknown", "wireplumber 1.0.0"):
            with self.subTest(version=version), patch.object(policy.subprocess, "run") as command:
                command.return_value = subprocess.CompletedProcess([], 0, version, "")
                with self.assertRaises(ValueError):
                    policy.installed_series()


if __name__ == "__main__":
    unittest.main()
