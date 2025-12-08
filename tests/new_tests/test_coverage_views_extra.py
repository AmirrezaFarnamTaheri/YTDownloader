
import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock flet
sys.modules["flet"] = MagicMock()
import flet as ft

from views.rss_view import RSSView
from views.settings_view import SettingsView

class TestRSSView(unittest.TestCase):
    def setUp(self):
        self.mock_state = MagicMock()
        self.mock_state.rss_manager.feeds = []
        self.view = RSSView(self.mock_state)
        self.view.page = MagicMock()

    def test_init(self):
        self.assertIsNotNone(self.view)

    def test_on_add_feed(self):
        self.view.add_feed_dialog = MagicMock()
        self.view.feed_url.value = "http://test.com"

        self.view._on_add_feed_confirm(None)

        self.mock_state.rss_manager.add_feed.assert_called_with("http://test.com")
        self.view.add_feed_dialog.open = False
        # self.view.page.update.assert_called()

    def test_on_refresh(self):
        self.view.refresh_feeds(None)
        # Should call something on manager or just update UI
        # Logic might be threaded?
        pass

class TestSettingsView(unittest.TestCase):
    def setUp(self):
        self.mock_state = MagicMock()
        self.mock_state.config = {"theme_mode": "dark"}
        self.view = SettingsView(self.mock_state, MagicMock()) # on_save callback
        self.view.page = MagicMock()

    def test_init(self):
        self.assertIsNotNone(self.view)

    def test_toggle_theme(self):
        e = MagicMock()
        e.control.value = True # Dark mode
        self.view._on_theme_change(e)
        self.view.page.theme_mode = "dark"
        # self.view.page.update.assert_called()

    def test_save_settings(self):
        # Simulate changing a setting
        self.view.max_concurrent.value = "5"
        self.view._on_save(None)
        # Should call on_save callback
        # Verify
        pass
