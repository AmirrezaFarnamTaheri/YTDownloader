"""
Extra coverage tests for main.py integration.
"""

import sys
import threading
import unittest
from unittest.mock import ANY, MagicMock, patch

import flet as ft

from main import global_crash_handler, main

# We need to mock setup_logging BEFORE importing main, because main calls it at module level
# But we can't easily do that with standard import unless we use patch.dict or similar on sys.modules
# OR we verify it was called by inspecting the side effects if possible.
# Actually, the test failing on `mock_setup_logging.assert_called()` means the mock passed to test function wasn't called.
# That mock is from `@patch("main.setup_logging")`.
# If `main.setup_logging` is imported as `from logger_config import setup_logging` in main.py,
# patching `main.setup_logging` should work for calls *inside* functions in main.py.
# BUT `setup_logging()` is called at module level in `main.py`.
# Module level code runs when imported. `from main import main` runs it.
# So by the time we patch it in test, it's too late.

# Strategy: Don't test module-level calls via patching for "main" function execution.
# The `main` function itself doesn't call `setup_logging`.
# `main.py` calls it globally.
# So checking `mock_setup_logging.assert_called()` inside `test_main_function` is wrong if we expect `main()` to call it.
# `main()` does NOT call it. It's called when module loads.


class TestMainIntegration(unittest.TestCase):

    def setUp(self):
        # Mock UIManager to avoid complex UI setup
        self.patcher_ui = patch("main.UIManager")
        self.mock_ui_class = self.patcher_ui.start()

        # Configure UIManager instance mock
        self.mock_ui = self.mock_ui_class.return_value
        self.mock_ui.initialize_views.return_value = MagicMock()
        self.mock_ui.download_view = MagicMock()

    def tearDown(self):
        self.patcher_ui.stop()

    @patch("main.state", new_callable=MagicMock)
    @patch("app_layout.AppLayout")
    @patch("flet.app")
    def test_main_function(self, mock_flet_app, mock_app_layout, mock_state):
        # Mock sys.argv
        with patch.object(sys, "argv", ["main.py"]):
            # We need to pass a Mock page to main
            mock_page = MagicMock()
            mock_page.width = 1200

            main(mock_page)

            # Check basic initializations
            # setup_logging is called at import time, not inside main()
            self.mock_ui_class.assert_called_with(mock_page)
            self.mock_ui.initialize_views.assert_called()
            mock_page.add.assert_called()  # View added

    @patch("main.sys.exit")
    @patch("builtins.print")
    def test_global_crash_handler(self, mock_print, mock_exit):
        # Simulate crash
        try:
            raise ValueError("Test Crash")
        except ValueError:
            # Capture exc info
            exc_type, exc_value, exc_traceback = sys.exc_info()
            global_crash_handler(exc_type, exc_value, exc_traceback)

        mock_exit.assert_called_with(1)
