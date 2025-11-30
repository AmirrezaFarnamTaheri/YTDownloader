import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import pyperclip

from app_state import state
from clipboard_monitor import _clipboard_loop, start_clipboard_monitor


class TestClipboardMonitorCoverage(unittest.TestCase):

    def setUp(self):
        state.shutdown_flag = threading.Event()
        state.clipboard_monitor_active = False
        state.last_clipboard_content = ""

    def tearDown(self):
        state.shutdown_flag.set()

    @patch("pyperclip.paste")
    def test_start_monitor_success(self, mock_paste):
        mock_paste.return_value = "test"

        with patch("threading.Thread") as mock_thread:
            start_clipboard_monitor(None, None)
            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()

    @patch("pyperclip.paste")
    def test_start_monitor_failure(self, mock_paste):
        mock_paste.side_effect = pyperclip.PyperclipException("No clipboard")

        with patch("threading.Thread") as mock_thread:
            start_clipboard_monitor(None, None)
            mock_thread.assert_not_called()

    @patch("pyperclip.paste")
    def test_loop_url_detection(self, mock_paste):
        mock_paste.return_value = "https://example.com"
        state.clipboard_monitor_active = True

        download_view = MagicMock()
        download_view.url_input.value = ""  # Empty

        page = MagicMock()

        # We need to run the loop for one iteration.
        # Since loop has while, we can't easily break it unless we set shutdown flag.
        # But loop calls sleep(2). We can patch time.sleep.

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = (
                lambda x: state.shutdown_flag.set()
            )  # Stop after first sleep

            _clipboard_loop(page, download_view)

            # Since mock_paste returns a URL, and it's valid (ui_utils.validate_url handles it),
            # it should update view.
            self.assertEqual(download_view.url_input.value, "https://example.com")
            page.open.assert_called()

    @patch("pyperclip.paste")
    def test_loop_exception_handling(self, mock_paste):
        # First call works, second raises exception
        state.clipboard_monitor_active = True

        mock_paste.side_effect = Exception("General Error")

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda x: state.shutdown_flag.set()

            # Should not crash
            _clipboard_loop(None, None)

    @patch("pyperclip.paste")
    def test_loop_clipboard_exception(self, mock_paste):
        state.clipboard_monitor_active = True
        mock_paste.side_effect = pyperclip.PyperclipException("Lost")

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda x: state.shutdown_flag.set()

            _clipboard_loop(None, None)

            # Should disable monitor
            self.assertFalse(state.clipboard_monitor_active)
