"""
Extended robustness tests for downloader logic.
"""

import unittest
from unittest.mock import MagicMock, patch

from downloader.core import download_video
from downloader.types import DownloadOptions


class TestDownloaderRobustness(unittest.TestCase):

    @patch("yt_dlp.YoutubeDL")
    def test_download_video_invalid_args(self, mock_ydl):
        # Invalid url type - TypeError is raised by 'in' operator in TelegramExtractor check if url is int
        # OR by logger formatting.
        # Let's expect TypeError as that's what happens when int is passed to string operations
        with self.assertRaises(TypeError):
            options = DownloadOptions(url=123)
            download_video(options)

    @patch("yt_dlp.YoutubeDL")
    def test_download_video_force_generic(self, mock_ydl):
        # Check if force_generic flag bypasses yt-dlp
        mock_hook = MagicMock()
        item = {}

        # Core doesn't use GenericExtractor or download_generic directly anymore in some paths
        # It uses GenericDownloader.download
        with patch("downloader.core.GenericDownloader.download") as mock_download:

            options = DownloadOptions(
                url="http://url.com",
                progress_hook=mock_hook,
                download_item=item,
                force_generic=True
            )
            download_video(options)

            mock_download.assert_called()
            mock_ydl.assert_not_called()

    @patch("yt_dlp.YoutubeDL")
    @patch("downloader.core.YTDLPWrapper.supports")
    def test_download_video_telegram(self, mock_supports, mock_ydl):
        mock_hook = MagicMock()
        item = {}
        mock_supports.return_value = False

        with patch(
            "downloader.core.TelegramExtractor.is_telegram_url", return_value=True
        ), patch("downloader.core.TelegramExtractor.extract") as mock_extract, patch(
            "downloader.core.GenericDownloader.download"
        ) as mock_download:

            mock_extract.return_value = {
                "title": "Tel",
                "video_streams": [{"url": "http://t.me/v", "ext": "mp4"}],
            }

            options = DownloadOptions(
                url="https://t.me/123",
                progress_hook=mock_hook,
                download_item=item
            )

            download_video(options)

            mock_extract.assert_called()

    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_exception(self, mock_wrapper):
        mock_wrapper.return_value.download.side_effect = Exception("Downloader failed")

        options = DownloadOptions(url="http://fail.com")
        with self.assertRaises(Exception):
            download_video(options)
