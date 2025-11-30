import time
import unittest
from unittest.mock import MagicMock, patch

import pyperclip

from app_state import state
from clipboard_monitor import _clipboard_loop, start_clipboard_monitor


class TestClipboardMonitorCoverage(unittest.TestCase):
    def setUp(self):
        state.clipboard_monitor_active = True
        state.last_clipboard_content = ""
        state.shutdown_flag.clear()

        self.page = MagicMock()
        self.download_view = MagicMock()
        self.download_view.url_input.value = ""

    @patch("pyperclip.paste")
    @patch("time.sleep", side_effect=InterruptedError)  # Break the loop
    @patch("ui_utils.validate_url", return_value=True)
    def test_clipboard_loop_detects_url(self, mock_validate, mock_sleep, mock_paste):
        mock_paste.return_value = "http://example.com"

        # We need to run it once.
        # _clipboard_loop logic:
        # while not shutdown:
        #    sleep
        #    paste
        #    check

        # sleep throws InterruptedError to break loop.
        # But wait, sleep is called BEFORE paste.
        # So if sleep raises, paste is never called.

        # We need sleep to NOT raise on first call, but raise on second call?
        # Or mock shutdown flag.

        # Let's mock sleep to do nothing, and set shutdown_flag after one iteration.
        # But loop condition is checked at start.

        # Approach: Mock sleep to set shutdown flag.
        def stop_loop(*args):
            state.shutdown_flag.set()

        mock_sleep.side_effect = stop_loop

        _clipboard_loop(self.page, self.download_view)

        self.assertEqual(state.last_clipboard_content, "http://example.com")
        self.assertEqual(self.download_view.url_input.value, "http://example.com")

    @patch("pyperclip.paste")
    @patch("time.sleep")
    @patch("ui_utils.validate_url", return_value=False)
    def test_clipboard_loop_ignores_invalid_url(
        self, mock_validate, mock_sleep, mock_paste
    ):
        mock_paste.return_value = "invalid url"

        def stop_loop(*args):
            state.shutdown_flag.set()

        mock_sleep.side_effect = stop_loop

        _clipboard_loop(self.page, self.download_view)

        self.assertEqual(state.last_clipboard_content, "invalid url")
        self.assertNotEqual(self.download_view.url_input.value, "invalid url")

    @patch("pyperclip.paste")
    def test_start_monitor_no_clipboard(self, mock_paste):
        mock_paste.side_effect = pyperclip.PyperclipException("No clipboard")

        start_clipboard_monitor(self.page, self.download_view)
        # Should catch exception and log warning (implied, no return/thread check easy here without further mocking)

    @patch("threading.Thread")
    @patch("pyperclip.paste")
    def test_start_monitor_success(self, mock_paste, mock_thread):
        mock_paste.return_value = "test"
        start_clipboard_monitor(self.page, self.download_view)
        mock_thread.assert_called_once()
