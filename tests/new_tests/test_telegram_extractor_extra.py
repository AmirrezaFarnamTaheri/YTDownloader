import unittest
from unittest.mock import patch, MagicMock
from downloader.extractors.telegram import TelegramExtractor


class TestTelegramExtractorExtra(unittest.TestCase):
    def test_extract_embed_url_logic(self):
        """Test URL normalization with embed parameter."""
        with patch("downloader.extractors.telegram.requests.get") as mock_get:
            # Test URL already having embed
            TelegramExtractor.extract("http://t.me/c/1?embed=1")
            args, _ = mock_get.call_args
            self.assertEqual(args[0], "http://t.me/c/1?embed=1")

    def test_extract_title_fallback(self):
        """Test title extraction fallback when text is empty."""
        with patch("downloader.extractors.telegram.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # HTML with video but empty text
            mock_response.text = """
                <html>
                    <video src="http://video.mp4"></video>
                    <div class="tgme_widget_message_text"></div>
                </html>
            """
            mock_get.return_value = mock_response

            info = TelegramExtractor.extract("http://t.me/c/123")
            self.assertEqual(info["title"], "Telegram_123")


if __name__ == "__main__":
    unittest.main()
