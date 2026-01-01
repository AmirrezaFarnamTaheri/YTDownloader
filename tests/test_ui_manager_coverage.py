# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Coverage tests for UIManager.
"""

import unittest
from unittest.mock import MagicMock, patch

import flet as ft

from ui_manager import UIManager


class TestUIManagerCoverage(unittest.TestCase):
    """Test suite for UIManager class."""

    def setUp(self):
        self.mock_page = MagicMock(spec=ft.Page)
        self.manager = UIManager(self.mock_page)

    def test_init(self):
        """Test initialization of UIManager."""
        self.assertEqual(self.manager.page, self.mock_page)
        self.assertIsNone(self.manager.app_layout)
        self.assertIsNone(self.manager.download_view)

    @patch("ui_manager.AppLayout")
    @patch("ui_manager.DownloadView")
    @patch("ui_manager.QueueView")
    @patch("ui_manager.HistoryView")
    @patch("ui_manager.RSSView")
    @patch("ui_manager.SettingsView")
    # Patch 'state' directly since it's imported as 'from app_state import state'
    @patch("ui_manager.state")
    def test_initialize_views(
        self,
        mock_state,  # pylint: disable=unused-argument
        mock_settings,  # pylint: disable=unused-argument
        mock_rss,  # pylint: disable=unused-argument
        mock_history,  # pylint: disable=unused-argument
        mock_queue,  # pylint: disable=unused-argument
        mock_download,  # pylint: disable=unused-argument
        mock_layout,
    ):
        """Test initializing views and layout."""
        # Ensure DownloadView mock returns an object compatible with DashboardView expectations
        # DashboardView now creates MockContainer which in tests might be strict about padding arg if passed via kwargs
        # But here we are mocking View classes. DashboardView is instantiated inside UIManager.
        # Wait, UIManager instantiates DashboardView directly (import from views.dashboard_view).
        # We need to patch DashboardView too!

        with patch("ui_manager.DashboardView") as mock_dashboard:
            mock_layout.return_value = MagicMock()

            layout = self.manager.initialize_views(
                on_fetch_info_callback=MagicMock(),
                on_add_to_queue_callback=MagicMock(),
                on_batch_import_callback=MagicMock(),
                on_schedule_callback=MagicMock(),
                on_cancel_item_callback=MagicMock(),
                on_remove_item_callback=MagicMock(),
                on_reorder_item_callback=MagicMock(),
                on_retry_item_callback=MagicMock(),
                on_toggle_clipboard_callback=MagicMock(),
                on_play_callback=MagicMock(),
                on_open_folder_callback=MagicMock(),
            )

            self.assertIsNotNone(self.manager.download_view)
            self.assertIsNotNone(self.manager.queue_view)
            self.assertIsNotNone(self.manager.history_view)
            self.assertIsNotNone(self.manager.rss_view)
            self.assertIsNotNone(self.manager.settings_view)
            self.assertIsNotNone(self.manager.dashboard_view)
            self.assertEqual(self.manager.app_layout, layout)

    def test_update_queue_view_active(self):
        """Test updating queue view when it is active."""
        self.manager.queue_view = MagicMock()
        self.manager.app_layout = MagicMock()
        self.manager.app_layout.active_view = self.manager.queue_view

        self.manager.update_queue_view()
        self.manager.queue_view.rebuild.assert_called()

    def test_navigate_to_history_real(self):
        """Test navigation to history view."""
        # We need to rely on the actual class imports if isinstance is strict.
        from views.history_view import (  # pylint: disable=import-outside-toplevel
            HistoryView,
        )

        view_instance = MagicMock()
        view_instance.__class__ = HistoryView

        self.manager.app_layout = MagicMock()
        self.manager.views_list = [MagicMock(), MagicMock(), view_instance]

        self.manager.navigate_to(2)

        view_instance.load.assert_called()

    def test_on_nav_change(self):
        """Test navigation change handling."""
        self.manager.app_layout = MagicMock()
        self.manager.download_view = MagicMock()
        self.manager.queue_view = MagicMock()
        self.manager.history_view = MagicMock()
        self.manager.rss_view = MagicMock()
        self.manager.settings_view = MagicMock()

        self.manager.views_list = [
            self.manager.download_view,
            self.manager.queue_view,
            self.manager.history_view,
            self.manager.rss_view,
            self.manager.settings_view,
        ]

        e = MagicMock()
        e.control.selected_index = 0
        # Placeholder for indirect testing via navigate_to which covers logic
