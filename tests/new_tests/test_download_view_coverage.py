import unittest
from unittest.mock import MagicMock, patch

import flet as ft

from app_state import AppState
from views.components.panels.base_panel import BasePanel
from views.components.panels.youtube_panel import YouTubePanel
from views.download_view import DownloadView


class TestDownloadViewCoverage(unittest.TestCase):
    def setUp(self):
        self.mock_page = MagicMock()
        self.mock_fetch = MagicMock()
        self.mock_add = MagicMock()
        self.mock_batch = MagicMock()
        self.mock_schedule = MagicMock()
        self.mock_state = MagicMock()
        self.mock_state.config = {"output_template": "%(title)s.%(ext)s"}

    def test_download_view_advanced_interactions(self):
        """Test interactions with advanced options."""
        view = DownloadView(
            self.mock_fetch,
            self.mock_add,
            self.mock_batch,
            self.mock_schedule,
            self.mock_state,
        )
        view.update = MagicMock()
        # Simulate page connection
        view.page = MagicMock()

        # 1. Test Advanced Options Toggle
        assert view.time_start.disabled is True
        assert view.time_end.disabled is True

        # 2. Test Cookies Selection
        view.cookies_dd.value = "chrome"
        # view.update() # No change handler

        # 3. Test Switches - Global generic one
        view.force_generic_cb.value = True

        # Note: Playlist switch is now in YouTubePanel, so we can't test it on base view alone
        # until a panel is loaded.

    def test_download_view_update_info_empty(self):
        """Test update_info with empty data."""
        view = DownloadView(
            self.mock_fetch,
            self.mock_add,
            self.mock_batch,
            self.mock_schedule,
            self.mock_state,
        )
        view.update = MagicMock()

        view.update_info(None)

        assert view.add_btn.disabled is True
        assert view.preview_card.visible is False
        # Panel should be None
        assert view.current_panel is None

    def test_download_view_update_info_full(self):
        """Test update_info with complex data."""
        view = DownloadView(
            self.mock_fetch,
            self.mock_add,
            self.mock_batch,
            self.mock_schedule,
            self.mock_state,
        )
        view.update = MagicMock()
        view.preview_card.update = MagicMock()

        info = {
            "title": "Test Video",
            "duration": "10:00",
            "thumbnail": "http://img.com",
            "original_url": "https://youtube.com/watch?v=123",
            "extractor": "youtube",
            "video_streams": [
                {
                    "format_id": "137",
                    "resolution": "1080p",
                    "ext": "mp4",
                    "filesize_str": "10.00 MB",
                },
            ],
            "audio_streams": [
                {"format_id": "140", "abr": "128", "ext": "m4a"},
            ],
        }

        view.update_info(info)

        # Check Panel Type
        assert isinstance(view.current_panel, YouTubePanel)

        # Check Panel content
        panel = view.current_panel
        assert len(panel.video_format_dd.options) == 2 # Best + 1 stream
        assert panel.audio_format_dd.visible is True

    def test_download_view_open_download_folder_error(self):
        """Test error handling when opening download folder."""
        view = DownloadView(
            self.mock_fetch,
            self.mock_add,
            self.mock_batch,
            self.mock_schedule,
            self.mock_state,
        )

        with patch("ui_utils.open_folder") as mock_open:
            mock_open.side_effect = Exception("Failed")
            # Should log error but not crash
            view._open_downloads_folder()
            mock_open.assert_called()

if __name__ == "__main__":
    unittest.main()
