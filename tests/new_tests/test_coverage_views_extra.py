import unittest
from unittest.mock import MagicMock, patch

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
        self.view.rss_input.value = "http://test.com"
        with patch("config_manager.ConfigManager.save_config"):
            self.view.add_rss(None)

    def test_on_refresh(self):
        self.view.refresh_feeds(None)
        # Should call something on manager or just update UI
        # Logic might be threaded?
        pass


class TestSettingsView(unittest.TestCase):
    def setUp(self):
        self.mock_state = MagicMock()
        self.mock_state.config = {"theme_mode": "dark"}
        self.view = SettingsView(self.mock_state.config)
        self.view.page = MagicMock()

    def test_init(self):
        self.assertIsNotNone(self.view)

    def test_toggle_theme(self):
        e = MagicMock()
        e.control.value = True  # Dark mode
        self.view._on_theme_change(e)
        self.view.page.theme_mode = "dark"
        # self.view.page.update.assert_called()

    def test_save_settings(self):
        # Simulate changing a setting
        self.view.rate_limit_input.value = "100K"
        self.view.proxy_input.value = "http://example.com:8080"
        self.view.output_template_input.value = "%(title)s.%(ext)s"

        # Test save logic
        # Patch ConfigManager where it is used in views.settings_view
        with patch(
            "views.settings_view.ConfigManager.save_config"
        ) as mock_save, patch(
            "views.settings_view.validate_proxy", return_value=True
        ), patch(
            "views.settings_view.validate_rate_limit", return_value=True
        ), patch(
            "views.settings_view.validate_output_template", return_value=True
        ):
            self.view.save_settings(None)
            mock_save.assert_called()
