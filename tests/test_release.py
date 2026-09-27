import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "upstream_release", ROOT / "scripts/release/upstream_release.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def series_fixture(series_id=1148921, version=1):
    return {
        "id": series_id,
        "version": version,
        "date": "2026-08-20T08:36:46",
        "project": {"link_name": "alsa-devel"},
        "submitter": {"email": release.AUTHOR},
        "name": "ALSA: add PreSonus Quantum PCI driver",
        "received_all": True,
        "total": 1,
        "patches": [{"id": 14758727, "msgid": "<rfc@example.com>", "name": "[RFC,1/1] Quantum"}],
    }


class ReleaseTests(unittest.TestCase):
    def test_rejects_unofficial_author_incomplete_series_and_non_rfc(self):
        for field, value in (
            ("submitter", {"email": "collaborator@example.com"}),
            ("project", {"link_name": "unofficial"}),
            ("received_all", False),
            ("total", 2),
            ("name", "Unrelated hardware"),
            ("patches", [{"msgid": "x@example.com", "name": "[PATCH] Quantum"}]),
            ("patches", [{"msgid": "../../bad", "name": "[RFC] Quantum"}]),
        ):
            with self.subTest(field=field, value=value):
                series = series_fixture()
                series[field] = value
                with self.assertRaises(ValueError):
                    release.validate_series(series)

    def test_discovery_skips_published_and_retries_draft(self):
        first = series_fixture()
        second = series_fixture(1149000, 2)
        patches = []
        for series in (first, second):
            patches.append({
                "submitter": series["submitter"], "name": "[RFC] Quantum",
                "series": [{key: series[key] for key in ("id", "date", "version")}],
            })
        with patch.object(release, "get_json", side_effect=[
            patches, first, {"draft": False}, second, {"draft": True},
        ]):
            self.assertEqual(release.discover("owner/repo"), 1149000)

    def test_api_failure_is_not_treated_as_new_release(self):
        error = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)
        series = series_fixture()
        patches = [{"submitter": series["submitter"], "name": "[RFC] Quantum", "series": [series]}]
        with patch.object(release, "get_json", side_effect=[patches, series, error]):
            with self.assertRaises(urllib.error.HTTPError):
                release.discover("owner/repo")

    def test_unofficial_feed_entries_cannot_trigger_release(self):
        entry = {"submitter": {"email": "other@example.com"}, "name": "[RFC] Quantum"}
        with patch.object(release, "get_json", return_value=[entry]) as get_json:
            self.assertIsNone(release.discover("owner/repo"))
            self.assertEqual(get_json.call_count, 1)

    def test_pagination_does_not_skip_oldest_unreleased(self):
        unrelated = {"submitter": {"email": "other@example.com"}, "name": "[RFC] Quantum"}
        series = series_fixture()
        eligible = {"submitter": series["submitter"], "name": "[RFC] Quantum", "series": [series]}
        missing = urllib.error.HTTPError("url", 404, "Not found", {}, None)
        with patch.object(release, "get_json", side_effect=[[unrelated] * 100, [eligible], series, missing]):
            self.assertEqual(release.discover("owner/repo"), 1148921)

    def test_raw_and_encoded_email_patches(self):
        raw = b"diff --git a/test b/test\n"
        self.assertEqual(release.decode_patch(raw), raw)
        encoded = (b"Content-Type: text/plain\nContent-Transfer-Encoding: base64\n\n"
                   b"ZGlmZiAtLWdpdCBhL3Rlc3QgYi90ZXN0Cg==\n")
        self.assertEqual(release.decode_patch(encoded), raw)
        with self.assertRaises(ValueError):
            release.decode_patch(b"<html>Access denied</html>")

    def test_multifile_series_is_applied_in_order_and_scoped(self):
        first_patch = b"""diff --git a/sound/pci/quantum/quantum_main.c b/sound/pci/quantum/quantum_main.c
new file mode 100644
--- /dev/null
+++ b/sound/pci/quantum/quantum_main.c
@@ -0,0 +1 @@
+original
diff --git a/unrelated.txt b/unrelated.txt
new file mode 100644
--- /dev/null
+++ b/unrelated.txt
@@ -0,0 +1 @@
+outside
"""
        second_patch = b"""diff --git a/sound/pci/quantum/quantum_main.c b/sound/pci/quantum/quantum_main.c
--- a/sound/pci/quantum/quantum_main.c
+++ b/sound/pci/quantum/quantum_main.c
@@ -1 +1 @@
-original
+updated
"""
        series = series_fixture(1149000)
        series["patches"].append(copy.deepcopy(series["patches"][0]))
        series["patches"][1]["id"] += 1
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(release, "download", side_effect=[first_patch, second_patch]):
                source, records, _ = release.extract_series(series, Path(temporary))
            self.assertEqual((source / "quantum_main.c").read_text(), "updated\n")
            self.assertFalse((Path(temporary) / "extracted/unrelated.txt").exists())
            self.assertEqual(len(records), 2)

    def test_symlinks_and_unexpected_source_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            (source / "file.c").symlink_to("/etc/passwd")
            with self.assertRaises(ValueError):
                release.source_hash(source)
            (source / "file.c").unlink()
            (source / "extra.sh").write_text("unexpected")
            with self.assertRaises(ValueError):
                release.source_hash(source)

    def test_archives_are_reproducible(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "package"
            source.mkdir()
            (source / "data.c").write_text("source")
            release.make_archive(source, root / "first.tar.gz", 1234)
            release.make_archive(source, root / "second.tar.gz", 1234)
            self.assertEqual((root / "first.tar.gz").read_bytes(), (root / "second.tar.gz").read_bytes())


if __name__ == "__main__":
    unittest.main()
