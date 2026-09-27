import importlib.util
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/release" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native = load_module("build_native")
apt = load_module("apt_repository")


class NativePackageTests(unittest.TestCase):
    def test_versions_are_scoped_to_rfc_and_packaging_revision(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            (bundle / "VERSION").write_text("20260820.rfc1.s1148921\n")
            self.assertEqual(native.package_version(bundle, "2"),
                             ("20260820.rfc1.s1148921", "20260820.rfc1.s1148921-2"))
            for revision in ("0", "-1", "1\nRequires: bad", "x"):
                with self.assertRaises(ValueError):
                    native.package_version(bundle, revision)
            (bundle / "VERSION").write_text("../../bad")
            with self.assertRaises(ValueError):
                native.package_version(bundle, "1")

    def test_stage_changes_dkms_version_not_driver_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            for name, content in {
                "module/dkms.conf": 'PACKAGE_VERSION="20260820.rfc1.s1148921"\n',
                "module/quantum_main.c": "unchanged RFC source\n",
                "module/COPYING": "GPL\n",
                "alsa/ucm2/P2626/HiFi.conf": "profile\n",
                "alsa/wireplumber/51-quantum2626.lua": "lua\n",
                "alsa/wireplumber/51-quantum2626.conf": "json\n",
                "quantum2626-backend.conf": "blacklist snd-quantum2626\n",
                "manifest.json": "{}\n",
                "README.md": "Readme\n",
                "LICENSE.repository": "MIT\n",
                "patches/1.patch": "RFC\n",
            }.items():
                native.write(bundle / name, content)
            destination = root / "stage"
            version = "20260820.rfc1.s1148921-2"
            native.stage(bundle, destination, version)
            source = destination / "usr/src" / f"quantum-{version}"
            self.assertEqual((source / "quantum_main.c").read_bytes(),
                             (bundle / "module/quantum_main.c").read_bytes())
            self.assertEqual((source / "dkms.conf").read_text(), f'PACKAGE_VERSION="{version}"\n')
            self.assertNotIn("-2", (bundle / "module/dkms.conf").read_text())

    def test_lifecycle_is_shell_syntax_valid_and_has_no_live_mutation(self):
        text = native.lifecycle("20260820.rfc1.s1148921-1", "configure_module")
        subprocess.run(["sh", "-n"], input=text, text=True, check=True)
        for command in ("modprobe", "rmmod", "systemctl", "service"):
            self.assertNotRegex(text, rf"(?m)^\s*{command}\s")
        self.assertIn('dkms remove -m quantum -v "$version" --all', text)

    def test_apt_requires_https_and_full_fingerprint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for fingerprint, url in (("short", "https://example.com"),
                                     ("A" * 40, "http://example.com"),
                                     ("A" * 40, "https://example.com/?bad")):
                with self.assertRaises(ValueError):
                    apt.build(root, root / "output", fingerprint, url)

    def run_lifecycle(self, root, action, headers=True, fail_build=False):
        modules = root / "modules"
        if headers:
            native.write(modules / "test-kernel/build/Makefile", "headers\n")
        executables = root / "bin"
        log = root / "calls"
        native.write(executables / "dkms", '''#!/bin/sh
printf '%s\\n' "$*" >> "$CALL_LOG"
if [ "$1" = build ] && [ "$FAIL_BUILD" = yes ]; then exit 7; fi
''', executable=True)
        native.write(executables / "depmod", '#!/bin/sh\nprintf "depmod %s\\n" "$*" >> "$CALL_LOG"\n',
                     executable=True)
        script = native.lifecycle("20260820.rfc1.s1148921-1", action)
        script = script.replace("/lib/modules/", str(modules) + "/")
        script = script.replace("/boot/", str(root / "boot") + "/")
        environment = dict(os.environ, PATH=f"{executables}:/usr/bin:/bin",
                           CALL_LOG=str(log), FAIL_BUILD="yes" if fail_build else "no")
        result = subprocess.run(["sh"], input=script, text=True, env=environment,
                                capture_output=True)
        return result, log.read_text() if log.exists() else ""

    def test_missing_headers_fail_before_dkms_registration(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, calls = self.run_lifecycle(Path(temporary), "configure_module", headers=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Install kernel headers", result.stderr)
            self.assertEqual(calls, "")

    def test_failed_build_is_not_reported_as_installed(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, calls = self.run_lifecycle(Path(temporary), "configure_module", fail_build=True)
            self.assertEqual(result.returncode, 7)
            self.assertNotIn("install -m", calls)
            self.assertNotIn("Quantum installed", result.stdout)

    def test_configuration_scopes_forced_install_and_refreshes_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, calls = self.run_lifecycle(Path(temporary), "configure_module")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("install -m quantum -v 20260820.rfc1.s1148921-1 -k test-kernel --force", calls)
            self.assertIn("depmod -a test-kernel", calls)

    def test_empty_apt_repository_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "No tested native packages"):
                apt.build(root, root / "output", "A" * 40, "https://example.com")

    def test_apt_discovery_ignores_drafts_and_incomplete_publication(self):
        releases = b'''[[
          {"tag_name":"rfc-20260820.rfc1.s1148921","draft":true,"assets":[]},
          {"tag_name":"rfc-20260820.rfc1.s1148921","draft":false,
           "assets":[{"name":"native-1-SHA256SUMS"}]}
        ]]'''
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(apt, "run", return_value=releases), patch.object(apt.subprocess, "run") as download:
                apt.download_packages("owner/repo", Path(temporary))
            download.assert_not_called()

    def test_apt_discovery_verifies_published_package_bytes(self):
        import json

        package_name = "quantum-dkms_20260820.rfc1.s1148921-1_amd64.deb"
        checksum_name = "native-1-SHA256SUMS"
        releases = [[{
            "tag_name": "rfc-20260820.rfc1.s1148921", "draft": False,
            "assets": [{"name": name} for name in (
                package_name, checksum_name, "native-1-build-evidence.tar.gz")],
        }]]
        payload = b"test package bytes"

        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as temporary:
                def download(arguments, **kwargs):
                    destination = Path(arguments[arguments.index("--dir") + 1])
                    (destination / package_name).write_bytes(payload)
                    digest = "0" * 64 if corrupt else hashlib.sha256(payload).hexdigest()
                    (destination / checksum_name).write_text(f"{digest}  {package_name}\n")

                with patch.object(apt, "run", return_value=json.dumps(releases).encode()), \
                        patch.object(apt.subprocess, "run", side_effect=download):
                    if corrupt:
                        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                            apt.download_packages("owner/repo", Path(temporary))
                    else:
                        apt.download_packages("owner/repo", Path(temporary))


if __name__ == "__main__":
    unittest.main()
