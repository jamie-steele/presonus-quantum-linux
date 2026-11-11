import http.client
import importlib.util
import io
import json
from pathlib import Path
import socket
import ssl
import unittest
from unittest.mock import MagicMock, call, patch
import urllib.error


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "upstream_release", ROOT / "scripts/release/upstream_release.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class ReleaseDownloadTests(unittest.TestCase):
    def response(self, payload):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = payload
        return response

    def test_transient_open_failures_retry_and_keep_stdout_clean(self):
        errors = [
            TimeoutError("read timed out"),
            ConnectionResetError("connection reset"),
            urllib.error.URLError(TimeoutError("connection timed out")),
            urllib.error.URLError(socket.gaierror(socket.EAI_AGAIN, "temporary DNS failure")),
        ]
        errors.extend(
            urllib.error.HTTPError("url", status, "temporary failure", {}, None)
            for status in (408, 429, 500, 502, 503, 504)
        )
        for error in errors:
            with self.subTest(error=error):
                with (
                    patch.object(release.urllib.request, "urlopen", side_effect=[
                        error, self.response(b"[]"),
                    ]) as urlopen,
                    patch.object(release.time, "sleep") as sleep,
                    patch.object(release.sys, "stderr", new_callable=io.StringIO) as stderr,
                    patch.object(release.sys, "stdout", new_callable=io.StringIO) as stdout,
                ):
                    self.assertEqual(release.download("https://example.com", "secret"), b"[]")
                    self.assertEqual(urlopen.call_count, 2)
                    sleep.assert_called_once_with(2)
                    self.assertIn("attempt 2/3", stderr.getvalue())
                    self.assertNotIn("secret", stderr.getvalue())
                    self.assertEqual(stdout.getvalue(), "")
                    request = urlopen.call_args.args[0]
                    self.assertEqual(request.get_header("Authorization"), "Bearer secret")
                    self.assertEqual(urlopen.call_args.kwargs, {"timeout": 60})

    def test_partial_read_is_discarded_before_retry(self):
        for error in (TimeoutError("read timed out"), http.client.IncompleteRead(b"partial")):
            with self.subTest(error=error):
                failed_response = self.response(b"")
                failed_response.__enter__.return_value.read.side_effect = error
                successful_response = self.response(b"complete")
                with (
                    patch.object(release.urllib.request, "urlopen", side_effect=[
                        failed_response, successful_response,
                    ]),
                    patch.object(release.time, "sleep"),
                    patch.object(release.sys, "stderr", new_callable=io.StringIO),
                ):
                    self.assertEqual(release.download("https://example.com"), b"complete")
                    failed_response.__exit__.assert_called_once()
                    successful_response.__enter__.return_value.read.assert_called_once_with(
                        release.MAX_RESPONSE + 1
                    )

    def test_exhausted_retries_propagate_failure_with_bounded_backoff(self):
        error = TimeoutError("read timed out")
        with (
            patch.object(release.urllib.request, "urlopen", side_effect=error) as urlopen,
            patch.object(release.time, "sleep") as sleep,
            patch.object(release.sys, "stderr", new_callable=io.StringIO),
        ):
            with self.assertRaises(TimeoutError) as raised:
                release.download("https://example.com")
            self.assertIs(raised.exception, error)
            self.assertEqual(urlopen.call_count, 3)
            self.assertEqual(sleep.call_args_list, [call(2), call(4)])

    def test_permanent_failures_are_not_retried(self):
        errors = [
            urllib.error.HTTPError("url", status, "permanent failure", {}, None)
            for status in (400, 401, 403, 404)
        ]
        errors.extend([
            urllib.error.URLError(ssl.SSLCertVerificationError("invalid certificate")),
            urllib.error.URLError(socket.gaierror(socket.EAI_NONAME, "unknown host")),
        ])
        for error in errors:
            with self.subTest(error=error):
                with (
                    patch.object(release.urllib.request, "urlopen", side_effect=error) as urlopen,
                    patch.object(release.time, "sleep") as sleep,
                ):
                    with self.assertRaises(type(error)):
                        release.download("https://example.com")
                    urlopen.assert_called_once()
                    sleep.assert_not_called()

    def test_invalid_json_and_oversized_payloads_are_not_retried(self):
        with (
            patch.object(release.urllib.request, "urlopen", return_value=self.response(b"invalid")) as urlopen,
            patch.object(release.time, "sleep") as sleep,
        ):
            with self.assertRaises(json.JSONDecodeError):
                release.get_json("https://example.com")
            urlopen.assert_called_once()
            sleep.assert_not_called()

        with (
            patch.object(release, "MAX_RESPONSE", 4),
            patch.object(release.urllib.request, "urlopen", return_value=self.response(b"large")) as urlopen,
            patch.object(release.time, "sleep") as sleep,
        ):
            with self.assertRaisesRegex(ValueError, "Response exceeds"):
                release.download("https://example.com")
            urlopen.assert_called_once()
            sleep.assert_not_called()
