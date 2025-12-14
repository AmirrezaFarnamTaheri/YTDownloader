import sys
import unittest
from unittest.mock import MagicMock, patch

from downloader.extractors.telegram import TelegramExtractor

class TestTelegramExtractor(unittest.TestCase):
    def test_is_telegram_url(self):
        with patch("downloader.extractors.telegram.validate_url", return_value=True):
            self.assertTrue(TelegramExtractor.is_telegram_url("https://t.me/c/123"))

    @patch("downloader.extractors.telegram.BeautifulSoup")
    @patch("requests.get")
    def test_get_metadata_success(self, mock_get, mock_bs):
        # Mock Response object
        mock_resp = MagicMock()
        # Ensure iter_content returns an iterator
        mock_resp.iter_content.return_value = iter(
            [
                b'<html><meta property="og:description" content="Title">',
                b'<video src="http://example.com/vid.mp4"></video></html>',
            ]
        )

        # Context manager
        mock_get.return_value.__enter__.return_value = mock_resp

        # Create a local MockTag class to patch the one imported in the module
        class MockTag:
            def get(self, key):
                return "http://example.com/vid.mp4"

        # Patch 'Tag' in the module under test to be our MockTag class
        with patch("downloader.extractors.telegram.Tag", MockTag):
            # Setup BeautifulSoup mock for this test
            mock_soup = mock_bs.return_value

            mock_video_tag = MockTag()

            # Side effect for find
            def find_side_effect(name, *args, **kwargs):
                if name == "video":
                    return mock_video_tag
                return None

            mock_soup.find.side_effect = find_side_effect

            info = TelegramExtractor.get_metadata("https://t.me/c/1")
            self.assertIsNotNone(info)
            self.assertEqual(info["url"], "http://example.com/vid.mp4")
            self.assertEqual(info["title"], "Telegram Video")

    @patch("requests.get")
    def test_get_metadata_large_response(self, mock_get):
        large_chunk = b"a" * (2 * 1024 * 1024 + 10)
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = iter([large_chunk])
        mock_get.return_value.__enter__.return_value = mock_resp

        info = TelegramExtractor.get_metadata("https://t.me/c/1")
        self.assertIsNone(info)

    @patch("requests.get")
    def test_get_metadata_no_video(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = iter([b"<html></html>"])
        mock_get.return_value.__enter__.return_value = mock_resp

        info = TelegramExtractor.get_metadata("https://t.me/c/1")
        self.assertIsNone(info)

    @patch("downloader.extractors.telegram.TelegramExtractor.get_metadata")
    @patch("downloader.engines.generic.GenericDownloader.download")
    def test_extract_success(self, mock_download, mock_meta):
        mock_meta.return_value = {"url": "http://v.mp4", "title": "Vid"}

        TelegramExtractor.extract("http://t.me/1", "out_path")

        mock_download.assert_called()
        args = mock_download.call_args
        self.assertEqual(args[0][0], "http://v.mp4")
        self.assertEqual(args[1]["filename"], "Vid.mp4")

    def test_extract_fail(self):
        with patch(
            "downloader.extractors.telegram.TelegramExtractor.get_metadata",
            return_value=None,
        ):
            with self.assertRaises(ValueError):
                TelegramExtractor.extract("http://t.me/1", "path")
