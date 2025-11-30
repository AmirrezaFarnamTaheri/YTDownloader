import logging
import os
import signal
import sys
import unittest
from unittest.mock import MagicMock, patch

from main import global_crash_handler, main, setup_logging


class TestMainIntegration(unittest.TestCase):
    def setUp(self):
        # Reset logging handlers
        logging.getLogger().handlers = []

    def test_setup_logging(self):
        setup_logging()
        logger = logging.getLogger()
        self.assertTrue(len(logger.handlers) > 0)
        # Verify handlers (FileHandler and StreamHandler)
        has_file_handler = any(
            isinstance(h, logging.FileHandler) for h in logger.handlers
        )
        has_stream_handler = any(
            isinstance(h, logging.StreamHandler) for h in logger.handlers
        )
        self.assertTrue(has_file_handler)
        self.assertTrue(has_stream_handler)

    @patch("builtins.print")
    def test_global_crash_handler(self, mock_print):
        # Test the exception handler
        ex_type = ValueError
        ex_value = ValueError("Test error")
        ex_traceback = None

        with self.assertRaises(SystemExit):
            global_crash_handler(ex_type, ex_value, ex_traceback)

    @patch("builtins.open", new_callable=MagicMock)
    @patch("builtins.print")
    def test_global_crash_handler_file_write(self, mock_print, mock_open):
        ex_type = ValueError
        ex_value = ValueError("Test error")
        ex_traceback = None

        with self.assertRaises(SystemExit):
            global_crash_handler(ex_type, ex_value, ex_traceback)

        mock_open.assert_called()

    @patch("main.state", new_callable=MagicMock)
    @patch("main.AppLayout")  # Mock AppLayout to prevent 'must be added to page' error
    @patch("flet.app")
    @patch("main.setup_logging")
    def test_main_function(
        self, mock_setup_logging, mock_flet_app, mock_app_layout, mock_state
    ):
        # Mock sys.argv
        with patch.object(sys, "argv", ["main.py"]):
            # We need to pass a Mock page to main
            mock_page = MagicMock()
            main(mock_page)

            mock_page.add.assert_called()  # AppLayout added

    @patch("signal.signal")
    @patch("signal.alarm")
    def test_startup_timeout_linux(self, mock_alarm, mock_signal):
        # Verify signal handling on Linux (simulated)
        with patch("sys.platform", "linux"):
            # We also need to mock os.name because main.py checks os.name != "nt"
            with patch("os.name", "posix"):
                from main import startup_timeout

                with startup_timeout(1):
                    pass
                mock_alarm.assert_called()

    def test_startup_timeout_windows(self):
        # Verify signal handling on Windows (simulated)
        with patch("os.name", "nt"):
            from main import startup_timeout

            with startup_timeout(1):
                pass
            # Should just yield and log warning
