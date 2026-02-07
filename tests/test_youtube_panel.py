from unittest.mock import MagicMock

import flet as ft
import pytest

from views.components.panels.youtube_panel import YouTubePanel


class TestYouTubePanel:
    @pytest.fixture
    def mock_info(self):
        return {
            "title": "Test Video",
            "video_streams": [
                {
                    "format_id": "137",
                    "resolution": "1080p",
                    "ext": "mp4",
                    "filesize": 1048576,
                },
                {
                    "format_id": "22",
                    "resolution": "720p",
                    "ext": "mp4",
                    "filesize_str": "50MB",
                },
            ],
            "audio_streams": [{"format_id": "140", "abr": 128, "ext": "m4a"}],
            "subtitles": {"en": [{"url": "http://sub.srt"}]},
            "_type": "video",
        }

    @pytest.fixture
    def panel(self, mock_info):
        return YouTubePanel(mock_info, lambda: None)

    def test_init_structure(self, panel):
        assert isinstance(panel.video_format_dd, ft.Dropdown)
        assert isinstance(panel.audio_format_dd, ft.Dropdown)
        assert isinstance(panel.subtitle_dd, ft.Dropdown)
        assert isinstance(panel.sponsorblock_cb, ft.Switch)
        assert isinstance(panel.playlist_cb, ft.Switch)
        assert isinstance(panel.chapters_cb, ft.Switch)

    def test_populate_options_video(self, panel):
        # Check video options
        opts = panel.video_format_dd.options
        # Expect "best" + 2 streams
        assert len(opts) == 3
        assert opts[0].key == "best"
        assert opts[1].key == "137"  # format_id
        # Check filesize formatting
        assert "1.0 MB" in opts[1].text
        assert "50MB" in opts[2].text

    def test_populate_options_audio(self, panel):
        # Audio dropdown should be visible
        assert panel.audio_format_dd.visible is True
        opts = panel.audio_format_dd.options
        assert len(opts) == 1
        assert opts[0].key == "140"
        assert "128k" in opts[0].text

    def test_populate_options_subtitles(self, panel):
        opts = panel.subtitle_dd.options
        # None + en
        assert len(opts) == 2
        assert opts[0].key == "None"
        assert opts[1].key == "en"

    def test_playlist_detection_video(self, panel):
        assert panel.playlist_cb.value is False
        assert panel.playlist_cb.disabled is True

    def test_playlist_detection_playlist(self):
        info = {"_type": "playlist", "title": "Test Playlist"}
        panel = YouTubePanel(info, lambda: None)
        assert panel.playlist_cb.value is True
        assert panel.playlist_cb.disabled is False

    def test_get_options(self, panel):
        # Default state
        opts = panel.get_options()
        assert opts["video_format"] == "best"
        assert opts["audio_format"] == "140"
        assert opts["subtitle_lang"] is None
        assert opts["sponsorblock"] is False
        assert opts["playlist"] is False
        assert opts["chapters"] is False

    def test_interactions(self, panel):
        # Change video format
        panel.video_format_dd.value = "137"

        # Enable SponsorBlock
        panel.sponsorblock_cb.value = True

        # Select Subtitle
        panel.subtitle_dd.value = "en"

        opts = panel.get_options()
        assert opts["video_format"] == "137"
        assert opts["sponsorblock"] is True
        assert opts["subtitle_lang"] == "en"

    def test_build(self, panel):
        container = panel.build()
        assert isinstance(container, ft.Container)
        content_col = container.content
        assert isinstance(content_col, ft.Column)
        # Check basic structure
        assert len(content_col.controls) > 0
