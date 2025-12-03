import unittest
from unittest.mock import ANY, MagicMock, Mock, patch

import flet as ft

from app_layout import AppLayout
from theme import Theme
from views.rss_view import RSSView
from views.settings_view import SettingsView


class DummyPage:
    def __init__(self):
        self.width = 1024
        self.controls = []
        self.overlay = []
        self.theme_mode = ft.ThemeMode.SYSTEM
        self.navigation_bar = None
        self.on_resized = None

    def update(self):
        pass

    def open(self, control):
        pass


class TestUIExtended(unittest.TestCase):

    def setUp(self):
        self.mock_page = DummyPage()
        self.mock_config = {"rss_feeds": ["http://feed.com"], "theme_mode": "Dark"}

    # --- RSSView Tests ---

    def test_rss_view_init(self):
        view = RSSView(self.mock_config)
        self.assertIsInstance(view.tabs, ft.Tabs)
        self.assertEqual(len(view.tabs.tabs), 2)

    def test_rss_view_tab_change(self):
        view = RSSView(self.mock_config)
        view.update = MagicMock()

        e = MagicMock()
        view.tabs.selected_index = 1
        view.on_tab_change(e)

        view.tabs.selected_index = 0
        view.on_tab_change(e)

    @patch("views.rss_view.RSSManager")
    def test_rss_view_fetch_feeds(self, MockRSS):
        view = RSSView(self.mock_config)
        view.update = MagicMock()

        view.rss_manager.get_all_items = MagicMock(
            return_value=[
                {
                    "title": "Video 1",
                    "link": "http://v1",
                    "published": "2023-01-01",
                    "feed_name": "F1",
                },
                {
                    "title": "Video 2",
                    "link": "http://v2",
                    "published": "2023-01-02",
                    "feed_name": "F2",
                },
            ]
        )

        view._fetch_feeds_task()

        self.assertEqual(len(view.items_list.controls), 2)
        view.rss_manager.get_all_items.assert_called()

    def test_rss_view_add_remove(self):
        view = RSSView(self.mock_config)
        view.update = MagicMock()
        view.rss_input.value = "http://newfeed.com"

        with patch("views.rss_view.ConfigManager.save_config") as mock_save:
            view.add_rss(None)

            found = False
            for f in self.mock_config["rss_feeds"]:
                url = f if isinstance(f, str) else f.get("url")
                if url == "http://newfeed.com":
                    found = True
                    break
            self.assertTrue(found)
            mock_save.assert_called()

            view.remove_rss("http://newfeed.com")

            found = False
            for f in self.mock_config["rss_feeds"]:
                url = f if isinstance(f, str) else f.get("url")
                if url == "http://newfeed.com":
                    found = True
                    break
            self.assertFalse(found)

    # --- AppLayout Tests ---

    def test_app_layout_init(self):
        nav_cb = MagicMock()
        clip_cb = MagicMock()

        # Verify type
        print(f"DEBUG: Type of mock_page is {type(self.mock_page)}")

        layout = AppLayout(self.mock_page, nav_cb, clip_cb)

        self.assertIsInstance(layout.view, ft.Row)
        self.assertIsInstance(layout.rail, ft.NavigationRail)

    def test_app_layout_clipboard_toggle(self):
        nav_cb = MagicMock()
        clip_cb = MagicMock()

        layout = AppLayout(self.mock_page, nav_cb, clip_cb)

        e = MagicMock()
        e.control.value = True
        layout._on_clipboard_toggle(e)

        clip_cb.assert_called_with(True)

    def test_app_layout_set_content(self):
        nav_cb = MagicMock()
        clip_cb = MagicMock()

        layout = AppLayout(self.mock_page, nav_cb, clip_cb)
        layout.content_area.update = MagicMock()

        content = ft.Text("New Content")
        layout.set_content(content)

        self.assertEqual(layout.content_area.content, content)
        layout.content_area.update.assert_called()

    # --- SettingsView Tests ---

    def test_settings_view_theme_toggle(self):
        view = SettingsView(self.mock_config)
        view.page = self.mock_page

        # Test Dark
        view.theme_mode_dd.value = "Dark"
        view._on_theme_change(None)
        self.assertEqual(self.mock_page.theme_mode, ft.ThemeMode.DARK)

        # Test Light
        view.theme_mode_dd.value = "Light"
        view._on_theme_change(None)
        self.assertEqual(self.mock_page.theme_mode, ft.ThemeMode.LIGHT)

        # Test System
        view.theme_mode_dd.value = "System"
        view._on_theme_change(None)
        self.assertEqual(self.mock_page.theme_mode, ft.ThemeMode.SYSTEM)

    def test_settings_view_save(self):
        view = SettingsView(self.mock_config)

        # Mocking open on the DummyPage
        self.mock_page.open = MagicMock()
        view.page = self.mock_page

        view.proxy_input.value = "http://proxy"
        view.theme_mode_dd.value = "Light"

        with patch("views.settings_view.ConfigManager.save_config") as mock_save:
            view.save_settings(None)
            self.assertEqual(self.mock_config["proxy"], "http://proxy")
            self.assertEqual(self.mock_config["theme_mode"], "Light")
            mock_save.assert_called()
            self.mock_page.open.assert_called()
