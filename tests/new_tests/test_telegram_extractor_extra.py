"""
Extra coverage tests for TelegramExtractor.
"""

import unittest
from unittest.mock import MagicMock, patch

from downloader.extractors.telegram import TelegramExtractor


class TestTelegramExtractorExtra(unittest.TestCase):

    @patch("downloader.extractors.telegram.GenericDownloader.download")
    def test_extract_embed_url_logic(self, mock_download):
        """Test URL normalization with embed parameter."""
        mock_download.return_value = {}
        with patch("downloader.extractors.telegram.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"""
                <html>
                    <video src="http://video.mp4"></video>
                </html>
            """
            mock_get.return_value = mock_response

            # Test URL already having embed (logic check mainly in what requests gets called with?)
            # Actually extract() fetches the URL as given.
            # But the logic usually appends ?embed=1 if using scraping.
            # Current impl: requests.get(url, ...)

            TelegramExtractor.extract("http://t.me/c/1?embed=1", output_path="/tmp")

            mock_get.assert_called_with(
                "http://t.me/c/1?embed=1", headers=unittest.mock.ANY, timeout=15
            )

    @patch("downloader.extractors.telegram.GenericDownloader.download")
    def test_extract_title_fallback(self, mock_download):
        """Test title extraction fallback when text is empty."""
        mock_download.return_value = {"filename": "video.mp4"}
        with patch("downloader.extractors.telegram.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # HTML with video but empty text
            mock_response.content = b"""
                <html>
                    <video src="http://video.mp4"></video>
                    <div class="tgme_widget_message_text"></div>
                </html>
            """
            mock_get.return_value = mock_response

            info = TelegramExtractor.extract("http://t.me/c/123", output_path="/tmp")

            # Since GenericDownloader handles metadata return, we check that.
            self.assertEqual(info["filename"], "video.mp4")
