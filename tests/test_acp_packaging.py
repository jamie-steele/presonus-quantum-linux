import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("acp_native", ROOT / "scripts/release/build_native.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class AcpPackagingTests(unittest.TestCase):
    def artifact(self, root):
        artifact = root / "artifact"
        artifact.mkdir()
        plugin = artifact / "libspa-alsa.so"
        plugin.write_bytes(b"test shared library payload")
        source_patch = ROOT / "packaging/pipewire/0001-stop-after-complete-ucm-profile.patch"
        metadata = {
            "router_sha256": hashlib.sha256((ROOT / "packaging/pipewire/plugin.c").read_bytes()).hexdigest(),
            "plugin_sha256": hashlib.sha256(plugin.read_bytes()).hexdigest(),
            "patch_sha256": hashlib.sha256(source_patch.read_bytes()).hexdigest(),
        }
        (artifact / "manifest.json").write_text(json.dumps(metadata))
        for name in ("COPYING", "LICENSE", "LGPL-2.1", "data/paths/test.conf", "source/build.py"):
            path = artifact / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n")
        return artifact

    def test_stage_installs_runtime_activation_data_and_corresponding_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = self.artifact(root)
            destination = root / "stage"
            native.stage_acp(artifact, destination)
            plugin = destination / "usr/lib/quantum-dkms/spa-0.2/alsa/libspa-alsa.so"
            self.assertEqual(plugin.read_bytes(), (artifact / "libspa-alsa.so").read_bytes())
            self.assertTrue((destination / "usr/share/quantum-dkms/acp/paths/test.conf").is_file())
            self.assertTrue((destination / "usr/share/doc/quantum-dkms/acp/source/build.py").is_file())
            dropin = destination / "usr/lib/systemd/user/wireplumber.service.d/51-quantum-acp.conf"
            self.assertIn('SPA_PLUGIN_DIR=/usr/lib/quantum-dkms/spa-0.2:', dropin.read_text())
            self.assertFalse((destination / "usr/lib/x86_64-linux-gnu/spa-0.2").exists())

    def test_changed_plugin_or_patch_is_rejected_before_staging(self):
        for field in ("plugin_sha256", "patch_sha256", "router_sha256"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                artifact = self.artifact(root)
                manifest = artifact / "manifest.json"
                metadata = json.loads(manifest.read_text())
                metadata[field] = "0" * 64
                manifest.write_text(json.dumps(metadata))
                destination = root / "stage"
                with self.assertRaises(ValueError):
                    native.stage_acp(artifact, destination)
                self.assertFalse(destination.exists())

    def test_native_build_rejects_patch_only_invocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/release/build_native.py"),
                str(Path(temporary) / "bundle"), str(output),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("--acp", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
