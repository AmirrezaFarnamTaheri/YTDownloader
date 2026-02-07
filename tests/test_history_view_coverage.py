# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Coverage tests for HistoryView.
"""

import unittest
from unittest.mock import MagicMock, patch

import flet as ft

from views.history_view import HistoryView


class TestHistoryViewCoverage(unittest.TestCase):
    """Test suite for HistoryView."""

    def setUp(self):
        self.mock_page = MagicMock()

    @patch("views.history_view.HistoryManager")
    def test_init(self, mock_history_manager):  # pylint: disable=unused-argument
        """Test HistoryView initialization."""
        view = HistoryView()
        self.assertIsInstance(view.history_list, ft.ListView)

    @patch("app_state.state")
    @patch("views.history_view.HistoryManager")
    def test_load_data(self, mock_history_manager, mock_state):
        """Test loading history data."""
        # Ensure state doesn't have a lingering manager that interferes with logic
        # Logic: hm = getattr(state, "history_manager", None) or HistoryManager()
        # If we set state.history_manager to None, it uses HistoryManager() (which is mocked).
        mock_state.history_manager = None

        view = HistoryView()
        view.page = self.mock_page

        # Mock history data as dicts (based on implementation)
        # return_value of the class constructor is the instance
        instance = mock_history_manager.return_value
        instance.get_history.return_value = [
            {
                "title": "Title",
                "url": "http://url",
                "timestamp": "2023",
                "file_size": "10MB",
                "filepath": "/tmp",
            }
        ]

        view.load()

        self.assertEqual(
            len(view.history_list.controls),
            1,
            "Should have exactly 1 history item control",
        )

        # Verify content
        control = view.history_list.controls[0]
        # Depending on HistoryItemControl implementation, we can check properties if accessible
        # or just assume it's correct if length matches.

    @patch("app_state.state")
    @patch("views.history_view.HistoryManager")
    def test_clear_history(self, mock_history_manager, mock_state):
        """Test clearing history."""
        mock_state.history_manager = None
        view = HistoryView()
        view.page = MagicMock()

        # Call clear_history
        view.clear_history(None)

        # It opens a dialog
        view.page.open.assert_called()

        # Get the dialog passed to open
        dlg = view.page.open.call_args[0][0]

        # Simulate confirming (Yes button is usually first or second)
        # In implementation: [Yes, No]
        yes_btn = dlg.actions[0]
        yes_btn.on_click(None)

        mock_history_manager.return_value.clear_history.assert_called()
        view.page.close.assert_called()

    @patch("views.history_view.open_folder")
    def test_open_folder_safe(self, mock_open_folder):
        """Test safe folder opening."""
        view = HistoryView()
        view.page = self.mock_page
        view.open_folder_safe("/tmp/path")
        mock_open_folder.assert_called_with("/tmp/path", self.mock_page)

        # Test exception
        mock_open_folder.side_effect = Exception("Fail")
        # Should not crash
        view.open_folder_safe("/tmp/path")
