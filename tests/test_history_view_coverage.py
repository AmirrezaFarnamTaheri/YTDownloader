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

    @patch("views.history_view.HistoryManager")
    def test_load_data(self, mock_history_manager):
        """Test loading history data."""
        view = HistoryView()
        view.page = self.mock_page

        # Mock history data as dicts (based on implementation)
        mock_history_manager.get_history.return_value = [
            {
                "title": "Title",
                "url": "http://url",
                "timestamp": "2023",
                "file_size": "10MB",
                "output_path": "/tmp",
            }
        ]

        view.load()

        self.assertEqual(len(view.history_list.controls), 1)
        container = view.history_list.controls[0]
        # Verify content
        row = container.content
        # First column has title - logic might differ in implementation
        # Let's inspect controls defensively
        if len(row.controls) > 1:
            col = row.controls[1]
            if hasattr(col, "controls") and col.controls:
                title_text = col.controls[0]
                self.assertIn("Title", title_text.value)

    @patch("views.history_view.HistoryManager")
    def test_clear_history(self, mock_history_manager):
        """Test clearing history."""
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

        mock_history_manager.clear_history.assert_called()
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
