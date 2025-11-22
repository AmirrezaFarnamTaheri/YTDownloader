import unittest
from unittest.mock import MagicMock, patch
from downloader.info import get_video_info
from downloader.core import download_video
from downloader.extractors.telegram import TelegramExtractor
from downloader.extractors.generic import GenericExtractor
from downloader.engines.generic import download_generic
import yt_dlp


class TestDownloaderRobustness(unittest.TestCase):

    @patch("yt_dlp.YoutubeDL")
    def test_get_video_info_success(self, mock_ydl):
        mock_instance = mock_ydl.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {
            "title": "Test Video",
            "duration_string": "10:00",
            "thumbnail": "http://thumb.com",
            "formats": [
                {"format_id": "1", "ext": "mp4", "vcodec": "h264", "acodec": "aac"}
            ],
        }

        info = get_video_info("http://youtube.com/watch?v=123")
        self.assertIsNotNone(info)
        self.assertEqual(info["title"], "Test Video")

    @patch("yt_dlp.YoutubeDL")
    def test_get_video_info_download_error_fallback(self, mock_ydl):
        # Simulate yt-dlp error
        mock_instance = mock_ydl.return_value.__enter__.return_value
        mock_instance.extract_info.side_effect = yt_dlp.utils.DownloadError("Fail")

        # Mock generic extractor fallback
        with patch("downloader.info.GenericExtractor.extract") as mock_generic:
            mock_generic.return_value = {
                "title": "Fallback Generic",
                "video_streams": [],
            }

            info = get_video_info("http://broken.com")
            self.assertIsNotNone(info)
            self.assertEqual(info["title"], "Fallback Generic")

    @patch("yt_dlp.YoutubeDL")
    def test_download_video_force_generic(self, mock_ydl):
        # Check if force_generic flag bypasses yt-dlp
        mock_hook = MagicMock()
        item = {}

        with patch("downloader.core.GenericExtractor.extract") as mock_generic, patch(
            "downloader.core.download_generic"
        ) as mock_download:

            mock_generic.return_value = {
                "title": "Forced",
                "video_streams": [{"url": "http://d.com", "ext": "mp4"}],
            }

            download_video("http://url.com", mock_hook, item, force_generic=True)

            mock_generic.assert_called()
            mock_download.assert_called()
            mock_ydl.assert_not_called()

    @patch("yt_dlp.YoutubeDL")
    def test_download_video_telegram(self, mock_ydl):
        mock_hook = MagicMock()
        item = {}

        with patch(
            "downloader.core.TelegramExtractor.is_telegram_url", return_value=True
        ), patch("downloader.core.TelegramExtractor.extract") as mock_extract, patch(
            "downloader.core.download_generic"
        ) as mock_download:

            mock_extract.return_value = {
                "title": "Tel",
                "video_streams": [{"url": "http://t.me/v", "ext": "mp4"}],
            }

            download_video("https://t.me/123", mock_hook, item)

            mock_extract.assert_called()
            mock_download.assert_called()
            mock_ydl.assert_not_called()


if __name__ == "__main__":
    unittest.main()
