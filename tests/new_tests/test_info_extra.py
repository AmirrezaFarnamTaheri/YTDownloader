"""
Extra coverage tests for downloader.info module.
"""

import unittest
from unittest.mock import patch

from downloader.info import get_video_info


class TestInfoExtra(unittest.TestCase):
    """Test suite for downloader.info extra coverage."""

    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_cookies_profile(self, mock_ydl):
        """Test cookies_from_browser_profile is passed correctly."""
        mock_ydl.return_value.__enter__.return_value.extract_info.return_value = {}

        get_video_info("http://url", "chrome", "profile1")

        args, _ = mock_ydl.call_args
        self.assertEqual(args[0]["cookies_from_browser"], ("chrome", "profile1"))

    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_subtitle_extraction_logic(self, mock_ydl):
        """Test subtitle extraction with different structures."""
        mock_info = {
            "subtitles": {
                "en": [{"ext": "vtt"}],
                "es": "not_list",  # Edge case for not being a list
            },
            "automatic_captions": {"fr": [{"ext": "srv3"}], "de": "not_list"},
        }
        mock_ydl.return_value.__enter__.return_value.extract_info.return_value = (
            mock_info
        )

        info = get_video_info("http://url")
        self.assertIn("en", info["subtitles"])
        self.assertIn("es", info["subtitles"])
        self.assertIn("fr (Auto)", info["subtitles"])
        self.assertIn("de (Auto)", info["subtitles"])

    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_direct_formats(self, mock_ydl):
        """Test direct format extraction."""
        mock_info = {
            "formats": [],
            "direct": True,
            "url": "http://direct.mp4",
            "ext": "mp4",
        }
        mock_ydl.return_value.__enter__.return_value.extract_info.return_value = (
            mock_info
        )

        info = get_video_info("http://url")
        self.assertEqual(len(info["video_streams"]), 1)
        self.assertEqual(info["video_streams"][0]["format_id"], "direct")


if __name__ == "__main__":
    unittest.main()
