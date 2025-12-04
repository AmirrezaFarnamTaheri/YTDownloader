"""
Tests for HistoryView coverage.
"""

from unittest.mock import MagicMock, patch

import flet as ft

from views.history_view import HistoryView


def test_history_view_open_folder_error():
    """Test exception handling in open_folder_safe."""
    view = HistoryView()
    # Mock page needed because open_folder_safe uses logging, but also it might use page for snackbar (not here though)
    # Actually open_folder is imported.

    with patch("views.history_view.open_folder", side_effect=Exception("Folder error")):
        with patch("views.history_view.logging.error") as mock_log_fn:
            view.open_folder_safe("/invalid/path")
            mock_log_fn.assert_called_with("Failed to open folder: Folder error")


def test_history_view_copy_url():
    """Test copy url button lambda."""
    # This is tricky to test fully without UI interaction, but we can verify the lambda structure
    # or simulate the click if we extract the logic.
    # The lambda is defined in _create_item.

    view = HistoryView()
    view.page = MagicMock()

    item = {"url": "http://test.com", "title": "Test", "output_path": "/tmp"}
    # pylint: disable=protected-access
    control = view._create_item(item)

    # Find the copy button (last icon button)
    # Structure: Container -> Row -> [Icon, Column, Container, IconButton(Folder), IconButton(Copy)]
    row = control.content
    copy_btn = row.controls[4]

    assert copy_btn.icon == ft.Icons.COPY

    # Execute the handler
    copy_btn.on_click(None)
    view.page.set_clipboard.assert_called_with("http://test.com")


def test_history_view_open_folder_click():
    """Test open folder button lambda."""
    view = HistoryView()
    view.open_folder_safe = MagicMock()

    item = {"url": "http://test.com", "title": "Test", "output_path": "/tmp"}
    # pylint: disable=protected-access
    control = view._create_item(item)

    row = control.content
    folder_btn = row.controls[3]

    folder_btn.on_click(None)
    view.open_folder_safe.assert_called_with("/tmp")
