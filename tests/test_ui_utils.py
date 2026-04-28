# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Unit tests for UI utility functions.
"""

import unittest
from unittest.mock import MagicMock, patch

from ui_utils import (
    format_file_size,
    is_ffmpeg_available,
    normalize_download_target,
    run_on_ui_thread,
    safe_request_with_redirects,
    validate_download_target,
    validate_download_path,
    validate_proxy,
    validate_rate_limit,
    validate_search_target,
    validate_url,
)


class TestUIUtils(unittest.TestCase):
    """Test cases for utility functions."""

    def test_validate_url(self):
        self.assertTrue(validate_url("https://www.youtube.com/watch?v=test"))
        self.assertFalse(validate_url("ftp://test.com"))
        self.assertFalse(validate_url("short"))

    @patch("socket.getaddrinfo")
    def test_validate_url_rejects_private_dns_resolution(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (None, None, None, None, ("10.0.0.7", 0)),
        ]

        self.assertFalse(validate_url("https://example.com/video", resolve_host=True))

    @patch("socket.getaddrinfo")
    def test_validate_url_accepts_public_dns_resolution(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (None, None, None, None, ("8.8.8.8", 0)),
        ]

        self.assertTrue(validate_url("https://example.com/video", resolve_host=True))

    def test_download_target_normalization(self):
        self.assertEqual(
            normalize_download_target("lofi study mix"),
            "ytsearch1:lofi study mix",
        )
        self.assertEqual(
            normalize_download_target("ytsearch5:ambient music"),
            "ytsearch5:ambient music",
        )
        self.assertTrue(validate_download_target("https://youtube.com/watch?v=abc"))
        self.assertFalse(validate_download_target("ytsearch0:bad count"))
        self.assertFalse(validate_download_target("file:///etc/passwd"))

    @patch("ui_utils.validate_url", return_value=True)
    @patch("ui_utils.requests.request")
    def test_safe_request_with_redirects_validates_each_hop(
        self, mock_request, mock_validate
    ):
        first = MagicMock()
        first.is_redirect = True
        first.is_permanent_redirect = False
        first.headers = {"Location": "https://example.com/final"}
        final = MagicMock()
        final.is_redirect = False
        final.is_permanent_redirect = False
        mock_request.side_effect = [first, final]

        result = safe_request_with_redirects("GET", "https://example.com/start")

        self.assertIs(result, final)
        self.assertEqual(mock_request.call_count, 2)
        mock_validate.assert_any_call("https://example.com/start", resolve_host=True)
        mock_validate.assert_any_call("https://example.com/final", resolve_host=True)

    def test_validate_search_target_limits_count_and_query(self):
        self.assertTrue(validate_search_target("ytsearch50:valid"))
        self.assertFalse(validate_search_target("ytsearch51:too many"))
        self.assertFalse(validate_search_target("ytsearch1:"))
        self.assertFalse(validate_search_target("ytsearch1:bad\x00query"))

    def test_validate_proxy(self):
        self.assertTrue(validate_proxy(""))
        self.assertFalse(validate_proxy("http://127.0.0.1:8080"))
        self.assertFalse(validate_proxy("invalid"))

    def test_validate_rate_limit(self):
        self.assertTrue(validate_rate_limit(""))
        self.assertTrue(validate_rate_limit("50K"))
        self.assertTrue(validate_rate_limit("10M"))
        self.assertFalse(validate_rate_limit("invalid"))

    def test_validate_download_path(self):
        self.assertTrue(validate_download_path(""))
        self.assertTrue(validate_download_path(None))
        self.assertFalse(validate_download_path(123))

    def test_format_file_size(self):
        self.assertEqual(format_file_size(None), "N/A")
        self.assertEqual(format_file_size(0), "0.00 B")
        self.assertEqual(format_file_size(1024), "1.00 KB")
        self.assertEqual(format_file_size(1048576), "1.00 MB")

    @patch("shutil.which")
    def test_is_ffmpeg_available_true(self, mock_which):
        import ui_utils

        # Reset cache
        ui_utils._ffmpeg_available_cache = None

        mock_which.return_value = "/usr/bin/ffmpeg"
        self.assertTrue(is_ffmpeg_available())

    @patch("shutil.which")
    def test_is_ffmpeg_available_false(self, mock_which):
        import ui_utils

        # Reset cache
        ui_utils._ffmpeg_available_cache = None

        mock_which.return_value = None
        self.assertFalse(is_ffmpeg_available())

    def test_run_on_ui_thread_wraps_sync_callback_as_async(self):
        page = MagicMock()
        captured = []
        page.run_task.side_effect = lambda cb: captured.append(cb)
        callback = MagicMock()

        run_on_ui_thread(page, callback, "value")

        self.assertEqual(len(captured), 1)

        import asyncio

        asyncio.run(captured[0]())
        callback.assert_called_once_with("value")

    def test_run_on_ui_thread_without_page_run_task_runs_sync_callback(self):
        page = object()
        callback = MagicMock()

        run_on_ui_thread(page, callback)

        callback.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
