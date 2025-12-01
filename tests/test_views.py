import unittest
from unittest.mock import MagicMock, patch
import os

import flet as ft

from app_state import AppState
from views.dashboard_view import DashboardView
from views.download_view import DownloadView
from views.history_view import HistoryView
from views.queue_view import QueueView
from views.rss_view import RSSView
from views.settings_view import SettingsView


class TestViews(unittest.TestCase):

    def setUp(self):
        self.page = MagicMock()
        self.state = AppState()
        # Clear queue in case it persists between tests (Singleton)
        with self.state.queue_manager._lock:
            self.state.queue_manager._queue = []

    def test_download_view_init(self):
        on_fetch = MagicMock()
        on_add = MagicMock()
        view = DownloadView(on_fetch, on_add, MagicMock(), MagicMock(), self.state)
        view._Control__page = MagicMock() # Mock page for update calls

        self.assertIsNotNone(view)
        # Check if controls are accessible directly or via components
        self.assertIsInstance(view.url_input, ft.TextField)

        # Test fetch trigger
        view.url_input.value = "http://test.com"
        view.fetch_btn.on_click(None)
        on_fetch.assert_called()

        # Test add trigger (should be disabled initially)
        # Enable it first or simulate info fetch
        view.add_btn.disabled = False
        view.add_btn.on_click(None)
        on_add.assert_called()

    def test_download_view_update_info(self):
        view = DownloadView(MagicMock(), MagicMock(), None, None, self.state)
        view._Control__page = MagicMock()
        view.update = MagicMock()

        # IMPORTANT: Mock page for child controls too because Flet checks it on update()
        view.preview_card._Control__page = MagicMock()

        info = {
            "title": "Test",
            "duration": 600,
            "duration_string": "10:00",
            "thumbnail": "http://thumb.com",
            "uploader": "Channel",
            "_type": "video"
        }
        view.update_video_info(info)

        # Verify preview card updated
        self.assertEqual(view.preview_card.title_text.value, "Test")
        self.assertEqual(view.preview_card.visible, True)

        # Verify button enabled
        self.assertFalse(view.add_btn.disabled)

    def test_queue_view_rebuild(self):
        on_cancel = MagicMock()
        on_remove = MagicMock()
        on_reorder = MagicMock()

        # Add item to queue
        item = {"url": "http://test.com", "status": "Queued", "title": "Test"}
        self.state.queue_manager.add_item(item)

        view = QueueView(self.state.queue_manager, on_cancel, on_remove, on_reorder)
        view._Control__page = MagicMock()
        view.rebuild()

        self.assertEqual(len(view.queue_list.controls), 1)

        # Test clear finished
        self.state.queue_manager.add_item(
            {"url": "http://done.com", "status": "Completed", "title": "Done"}
        )
        # Rebuild to reflect the added item
        view.rebuild()
        self.assertEqual(len(view.queue_list.controls), 2)

        view.clear_finished(None)
        on_remove.assert_called()

    @patch("history_manager.HistoryManager.get_history")
    def test_history_view_load(self, mock_get_history):
        mock_get_history.return_value = [
            {"url": "http://h.com", "title": "Hist", "status": "Completed"}
        ]
        view = HistoryView()
        view._Control__page = MagicMock()
        view.load()
        self.assertEqual(len(view.history_list.controls), 1)

    @patch("history_manager.HistoryManager.get_history")
    def test_dashboard_view_load(self, mock_get_history):
        mock_get_history.return_value = [{"url": "http://h.com"}]
        view = DashboardView()
        view._Control__page = MagicMock()
        view.load()
        # Check if stats card added
        self.assertEqual(len(view.stats_row.controls), 1)

    def test_rss_view(self):
        config = {"rss_feeds": []}
        view = RSSView(config)
        # Mock page
        view._Control__page = MagicMock()
        view.update = MagicMock()

        # Add feed
        view.rss_input.value = "http://rss.com"
        view.add_rss(None)

        # Verify it's in config (as list of dicts)
        feeds = config["rss_feeds"]
        self.assertEqual(len(feeds), 1)
        self.assertEqual(feeds[0]["url"], "http://rss.com")

        # Remove feed (pass dict)
        view.remove_rss({"url": "http://rss.com", "name": "http://rss.com"})
        self.assertEqual(len(config["rss_feeds"]), 0)

    @patch("config_manager.ConfigManager.save_config")
    def test_settings_view_save(self, mock_save):
        config = {"proxy": ""}
        view = SettingsView(config)
        view._Control__page = MagicMock()
        view.proxy_input.value = "http://proxy.com"
        view.save_settings(None)

        self.assertEqual(config["proxy"], "http://proxy.com")
        mock_save.assert_called()


if __name__ == "__main__":
    unittest.main()
