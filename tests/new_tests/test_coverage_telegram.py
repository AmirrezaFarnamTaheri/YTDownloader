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

        # Setup BeautifulSoup mock for this test
        # We need to ensure we're mocking the instance returned by the constructor
        mock_soup_instance = mock_bs.return_value

        # Prepare mock tags
        mock_video_tag = MagicMock(spec=Tag)
        mock_video_tag.get.return_value = "http://example.com/vid.mp4"

        mock_title_tag = MagicMock(spec=Tag)
        mock_title_tag.get.return_value = "Title"

        # Side effect to return specific tags based on arguments
        def find_side_effect(name, property=None, **kwargs):
            if name == "video":
                return mock_video_tag
            if name == "meta" and property == "og:description":
                return mock_title_tag
            return None

        mock_soup_instance.find.side_effect = find_side_effect

        # Ensure that when BS is instantiated, it returns our configured mock instance
        # Note: The test patches 'bs4.BeautifulSoup'
        # TelegramExtractor calls BeautifulSoup(content, "html.parser")

        info = TelegramExtractor.get_metadata("https://t.me/c/1")
        self.assertIsNotNone(info)
        self.assertEqual(info["url"], "http://example.com/vid.mp4")
        self.assertEqual(info["title"], "Title")

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
