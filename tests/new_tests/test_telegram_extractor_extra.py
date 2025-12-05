"""
Extra coverage tests for TelegramExtractor.
"""

import unittest
from unittest.mock import MagicMock, patch

from downloader.extractors.telegram import TelegramExtractor


class TestTelegramExtractorExtra(unittest.TestCase):
    """Test suite for TelegramExtractor extra coverage."""

    @patch("downloader.engines.generic.GenericDownloader.download")
    def test_extract_embed_url_logic(self, mock_download):
        """Test URL normalization with embed parameter."""
        mock_download.return_value = {}
        with patch("downloader.extractors.telegram.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Mock content iterator to return bytes
            mock_response.iter_content.return_value = [
                b"""
                <html>
                    <video src="http://video.mp4"></video>
                </html>
            """
            ]
            mock_get.return_value.__enter__.return_value = mock_response

            TelegramExtractor.extract("http://t.me/c/1?embed=1", output_path="/tmp")

            mock_get.assert_called_with(
                "http://t.me/c/1?embed=1",
                headers=unittest.mock.ANY,
                timeout=10,
                stream=True,
            )

    @patch("downloader.engines.generic.GenericDownloader.download")
    def test_extract_title_fallback(self, mock_download):
        """Test title extraction fallback when text is empty."""
        mock_download.return_value = {"filename": "video.mp4"}
        with patch("downloader.extractors.telegram.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # HTML with video but empty text
            mock_response.iter_content.return_value = [
                b"""
                <html>
                    <meta property="og:description" content="My Video">
                    <video src="http://video.mp4"></video>
                </html>
            """
            ]
            mock_get.return_value.__enter__.return_value = mock_response

            TelegramExtractor.extract("http://t.me/c/123", output_path="/tmp")

            mock_download.assert_called()
