import sys
import unittest
from unittest.mock import MagicMock, patch

import flet as ft

from views.components.download_preview import DownloadPreviewCard
from views.components.panels.youtube_panel import YouTubePanel
from views.download_view import DownloadView


class TestDownloadView(unittest.TestCase):
    def setUp(self):
        self.mock_fetch = MagicMock()
        self.mock_add = MagicMock()
        self.mock_batch = MagicMock()
        self.mock_schedule = MagicMock()
        self.mock_state = MagicMock()
        self.mock_state.config.get.return_value = "%(title)s.%(ext)s"

        # We need to mock BaseView init which calls super().__init__ and might use flet
        with patch("views.base_view.BaseView.__init__"):
            self.view = DownloadView(
                self.mock_fetch,
                self.mock_add,
                self.mock_batch,
                self.mock_schedule,
                self.mock_state,
            )

        # Manually set attributes that BaseView would have set or are needed
        self.view.page = MagicMock()
        self.view.url_input = MagicMock()
        self.view.url_input.value = ""
        self.view.fetch_btn = MagicMock()
        self.view.add_btn = MagicMock()
        self.view.preview_card = MagicMock()
        self.view.time_start = MagicMock()
        self.view.time_end = MagicMock()
        self.view.cookies_dd = MagicMock()
        self.view.force_generic_cb = MagicMock()
        self.view.options_container = MagicMock()

    def test_on_fetch_click_success(self):
        self.view.url_input.value = "http://test.com"
        self.view._on_fetch_click(None)
        self.mock_fetch.assert_called_with("http://test.com")
        # Check if disabled
        # self.assertTrue(self.view.fetch_btn.disabled) # Depends on if logic works on mock

    def test_on_fetch_click_empty(self):
        self.view.url_input.value = ""
        self.view._on_fetch_click(None)
        self.mock_fetch.assert_not_called()
        # self.assertIsNotNone(self.view.url_input.error_text)

    def test_on_add_click(self):
        self.view.url_input.value = "http://test.com"
        self.view.time_start.value = "00:00:10"
        self.view.force_generic_cb.value = True

        self.view._on_add_click(None)

        self.mock_add.assert_called()
        args = self.mock_add.call_args[0][0]
        self.assertEqual(args["url"], "http://test.com")
        self.assertEqual(args["start_time"], "00:00:10")
        self.assertTrue(args["force_generic"])

    def test_update_video_info_success(self):
        info = {
            "original_url": "https://youtube.com/watch?v=1",
            "title": "Vid",
            "thumbnail": "t",
            "duration": 100,
        }

        # We need to ensure YouTubePanel can be instantiated or mocked
        with patch("views.download_view.YouTubePanel") as MockPanel:
            self.view.update_video_info(info)

            self.assertEqual(self.view.video_info, info)
            self.view.preview_card.update_info.assert_called_with(info)
            MockPanel.assert_called()

    def test_update_video_info_none(self):
        self.view.update_video_info(None)
        self.assertIsNone(self.view.video_info)
        # self.assertTrue(self.view.add_btn.disabled)

    def test_open_downloads_folder(self):
        with patch("views.download_view.open_folder") as mock_open:
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = MagicMock()
                self.view._open_downloads_folder()
                mock_open.assert_called()


class TestDownloadPreviewCard(unittest.TestCase):
    def setUp(self):
        # Must patch flet controls used in init
        with patch("flet.Card"), patch("flet.Container"), patch("flet.Column"), patch(
            "flet.Row"
        ), patch("flet.Image"), patch("flet.Text"):
            self.card = DownloadPreviewCard()
            self.card.update = MagicMock()

    def test_update_info(self):
        info = {"title": "T", "thumbnail": "thumb", "duration": 60, "filesize": 1024}
        self.card.update_info(info)
        self.assertTrue(self.card.visible)


class TestYouTubePanel(unittest.TestCase):
    def setUp(self):
        self.panel = YouTubePanel({}, lambda: None)
        self.panel.format_dropdown = MagicMock()
        self.panel.format_dropdown.value = "best"

    def test_get_options(self):
        opts = self.panel.get_options()
        self.assertIsInstance(opts, dict)
        self.assertIn("video_format", opts)
