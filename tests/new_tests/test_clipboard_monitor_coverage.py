import unittest
from unittest.mock import MagicMock, patch
import pyperclip
from clipboard_monitor import _clipboard_loop, start_clipboard_monitor
from app_state import state


class TestClipboardMonitor(unittest.TestCase):
    def setUp(self):
        state.clipboard_monitor_active = True
        state.last_clipboard_content = None

    @patch("clipboard_monitor.pyperclip.paste")
    @patch("clipboard_monitor.validate_url")
    @patch("time.sleep")
    def test_clipboard_loop_detects_url(self, mock_sleep, mock_validate, mock_paste):
        # Setup
        state.shutdown_flag.clear()
        mock_paste.return_value = "https://example.com"
        mock_validate.return_value = True

        mock_download_view = MagicMock()
        mock_download_view.url_input.value = ""  # Empty input

        mock_page = MagicMock()

        # Mock shutdown_flag to run once then exit
        call_count = [0]
        original_is_set = state.shutdown_flag.is_set

        def is_set_side_effect():
            call_count[0] += 1
            return call_count[0] > 1

        state.shutdown_flag.is_set = is_set_side_effect

        try:
            # Execute
            _clipboard_loop(mock_page, mock_download_view)

            # Verify
            self.assertEqual(mock_download_view.url_input.value, "https://example.com")
            mock_page.open.assert_called_once()
            mock_page.update.assert_called_once()
        finally:
            state.shutdown_flag.is_set = original_is_set

    @patch("clipboard_monitor.pyperclip.paste")
    @patch("clipboard_monitor.validate_url")
    @patch("time.sleep")
    def test_clipboard_loop_ignores_existing_input(
        self, mock_sleep, mock_validate, mock_paste
    ):
        # Setup
        state.shutdown_flag.clear()
        mock_paste.return_value = "https://example.com"
        mock_validate.return_value = True

        mock_download_view = MagicMock()
        mock_download_view.url_input.value = "existing text"

        mock_page = MagicMock()

        # Mock shutdown_flag to run once then exit
        call_count = [0]
        original_is_set = state.shutdown_flag.is_set

        def is_set_side_effect():
            call_count[0] += 1
            return call_count[0] > 1

        state.shutdown_flag.is_set = is_set_side_effect

        try:
            # Execute
            _clipboard_loop(mock_page, mock_download_view)

            # Verify
            self.assertEqual(mock_download_view.url_input.value, "existing text")
            mock_page.open.assert_not_called()
        finally:
            state.shutdown_flag.is_set = original_is_set

    @patch("clipboard_monitor.pyperclip.paste")
    @patch("time.sleep")
    def test_clipboard_loop_handles_exception(self, mock_sleep, mock_paste):
        # Setup
        state.shutdown_flag.clear()
        mock_paste.side_effect = Exception("Clipboard error")

        mock_download_view = MagicMock()

        # Mock shutdown_flag to run once then exit
        call_count = [0]
        original_is_set = state.shutdown_flag.is_set

        def is_set_side_effect():
            call_count[0] += 1
            return call_count[0] > 1

        state.shutdown_flag.is_set = is_set_side_effect

        try:
            # Execute - should not raise
            _clipboard_loop(None, mock_download_view)
        finally:
            state.shutdown_flag.is_set = original_is_set

    @patch("clipboard_monitor.pyperclip.paste")
    @patch("time.sleep")
    def test_clipboard_loop_handles_pyperclip_exception(self, mock_sleep, mock_paste):
        # Setup
        state.shutdown_flag.clear()
        mock_paste.side_effect = pyperclip.PyperclipException("No xclip")

        mock_download_view = MagicMock()

        # Mock shutdown_flag to run once then exit
        call_count = [0]
        original_is_set = state.shutdown_flag.is_set

        def is_set_side_effect():
            call_count[0] += 1
            return call_count[0] > 1

        state.shutdown_flag.is_set = is_set_side_effect

        try:
            # Execute - should not raise
            _clipboard_loop(None, mock_download_view)
        finally:
            state.shutdown_flag.is_set = original_is_set

    @patch("threading.Thread")
    def test_start_clipboard_monitor(self, mock_thread):
        start_clipboard_monitor(None, None)
        mock_thread.assert_called_once()
