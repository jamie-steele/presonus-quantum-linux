import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "driver/scripts/host-tools.sh"


class HostToolsTests(unittest.TestCase):
    def test_wireplumber_legacy_debian_package_detection(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            wireplumber = directory / "wireplumber"
            wireplumber.write_text('#!/bin/bash\nexit 64\n')
            wireplumber.chmod(0o755)
            query = directory / "dpkg-query"
            for version, expected in (("0.4.8-4", "0.4"), ("1:0.5.8-1", "0.5"),
                                      ("1.0.0-1", None)):
                with self.subTest(version=version):
                    query.write_text(f'#!/bin/bash\nprintf "%s\\n" "{version}"\n')
                    query.chmod(0o755)
                    environment = dict(os.environ, PATH=temporary, WIREPLUMBER_SERIES="auto")
                    result = subprocess.run(["/bin/bash", str(TOOL), "wireplumber"],
                                            env=environment, text=True, capture_output=True)
                    if expected:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout.strip(), expected)
                    else:
                        self.assertNotEqual(result.returncode, 0)

    def test_initramfs_refresh_uses_each_tools_native_arguments(self):
        expected = {
            "update-initramfs": "-u -k test-kernel",
            "dracut": "--force --kver test-kernel",
            "mkinitcpio": "-P",
        }
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for command, arguments in expected.items():
                with self.subTest(command=command):
                    script = directory / command
                    script.write_text('#!/bin/bash\nprintf "%s\\n" "$*"\n')
                    script.chmod(0o755)
                    environment = dict(os.environ, PATH=temporary, INITRAMFS_TOOL=command)
                    result = subprocess.run(["/bin/bash", str(TOOL), "refresh", "test-kernel"],
                                            env=environment, text=True, capture_output=True, check=True)
                    self.assertEqual(result.stdout.strip(), arguments)

    def test_missing_explicit_initramfs_tool_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            environment = dict(os.environ, PATH=temporary, INITRAMFS_TOOL="dracut")
            result = subprocess.run(["/bin/bash", str(TOOL), "check"], env=environment, capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_wireplumber_detection_and_unknown_versions(self):
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "wireplumber"
            for version, expected in (("0.4.17", "0.4"), ("0.5.14", "0.5"), ("1.0.0", None)):
                with self.subTest(version=version):
                    script.write_text(f'#!/bin/bash\necho "wireplumber {version}"\n')
                    script.chmod(0o755)
                    environment = dict(os.environ, PATH=temporary, WIREPLUMBER_SERIES="auto")
                    result = subprocess.run(["/bin/bash", str(TOOL), "wireplumber"],
                                            env=environment, text=True, capture_output=True)
                    if expected:
                        self.assertEqual(result.returncode, 0)
                        self.assertEqual(result.stdout.strip(), expected)
                    else:
                        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
