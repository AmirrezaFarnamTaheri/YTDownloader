import unittest
from unittest.mock import MagicMock, patch

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
        view = DownloadView(on_fetch, on_add, None, None, self.state)

        self.assertIsNotNone(view)
        self.assertIsInstance(view.url_input, ft.TextField)

        # Test fetch trigger
        view.fetch_btn.on_click(None)
        on_fetch.assert_called()

        # Test add trigger
        view.download_btn.on_click(None)
        on_add.assert_called()

    def test_download_view_update_info(self):
        view = DownloadView(MagicMock(), MagicMock(), None, None, self.state)
        view._Control__page = MagicMock()
        info = {
            "title": "Test",
            "duration": "10:00",
            "thumbnail": "http://thumb.com",
            "video_streams": [
                {
                    "format_id": "1",
                    "resolution": "1080p",
                    "ext": "mp4",
                    "filesize": 1000,
                }
            ],
            "audio_streams": [],
        }
        view.update_info(info)
        self.assertEqual(view.title_text.value, "Test")
        self.assertEqual(view.video_format_dd.options[0].key, "1")

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

        # Add feed
        view.rss_input.value = "http://rss.com"
        view.add_rss(None)
        self.assertIn("http://rss.com", config["rss_feeds"])

        # Remove feed
        view.remove_rss("http://rss.com")
        self.assertNotIn("http://rss.com", config["rss_feeds"])

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
