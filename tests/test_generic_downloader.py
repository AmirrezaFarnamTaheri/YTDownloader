import unittest
from unittest.mock import MagicMock, patch
from generic_downloader import TelegramExtractor, GenericExtractor


class TestTelegramExtractor(unittest.TestCase):
    @patch("requests.get")
    def test_extract_telegram_video(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <meta property="og:video" content="https://example.com/video.mp4">
        <meta property="og:title" content="Test Video">
        <div class="tgme_widget_message_text">My Caption</div>
        </html>
        """
        mock_get.return_value = mock_response

        url = "https://t.me/channel/123"
        info = TelegramExtractor.extract(url)

        self.assertIsNotNone(info)
        self.assertTrue(info["is_telegram"])
        self.assertEqual(
            info["video_streams"][0]["url"], "https://example.com/video.mp4"
        )
        self.assertEqual(info["title"], "My Caption")

    @patch("requests.get")
    def test_extract_telegram_image(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <meta property="og:image" content="https://example.com/image.jpg">
        </html>
        """
        mock_get.return_value = mock_response

        url = "https://t.me/channel/456"
        info = TelegramExtractor.extract(url)

        self.assertIsNotNone(info)
        self.assertEqual(
            info["video_streams"][0]["url"], "https://example.com/image.jpg"
        )
        self.assertEqual(info["video_streams"][0]["ext"], "jpg")


class TestGenericExtractor(unittest.TestCase):
    @patch("requests.head")
    def test_extract_generic_file(self, mock_head):
        mock_response = MagicMock()
        mock_response.headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": "1048576",
            "Content-Disposition": 'attachment; filename="myfile.zip"',
        }
        mock_head.return_value = mock_response

        url = "https://example.com/download"
        info = GenericExtractor.extract(url)

        self.assertIsNotNone(info)
        self.assertTrue(info["is_generic"])
        self.assertEqual(info["title"], "myfile.zip")
        self.assertEqual(info["video_streams"][0]["filesize"], 1048576)

    @patch("requests.head")
    def test_extract_html_page(self, mock_head):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_head.return_value = mock_response

        url = "https://example.com/page"
        info = GenericExtractor.extract(url)

        self.assertIsNone(info)


if __name__ == "__main__":
    unittest.main()
