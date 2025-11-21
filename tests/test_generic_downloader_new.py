import unittest
from unittest.mock import MagicMock, patch
from generic_downloader import GenericExtractor, TelegramExtractor, download_generic
import responses
import os


class TestGenericDownloader(unittest.TestCase):

    @patch("requests.head")
    def test_generic_extractor_success(self, mock_head):
        mock_response = MagicMock()
        mock_response.headers = {
            "Content-Type": "video/mp4",
            "Content-Length": "1024",
            "Content-Disposition": 'attachment; filename="test_video.mp4"',
        }
        mock_head.return_value = mock_response

        url = "http://example.com/test_video.mp4"
        info = GenericExtractor.extract(url)

        self.assertIsNotNone(info)
        self.assertEqual(info["title"], "test_video.mp4")
        self.assertEqual(info["video_streams"][0]["filesize"], 1024)
        self.assertTrue(info["is_generic"])

    @patch("requests.head")
    def test_generic_extractor_html_fail(self, mock_head):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_head.return_value = mock_response

        url = "http://example.com/page"
        info = GenericExtractor.extract(url)

        self.assertIsNone(info)

    @patch("requests.get")
    def test_telegram_extractor_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <video src="https://cdn.telegram.org/file/video.mp4"></video>
            <div class="tgme_widget_message_text">Test Video Title</div>
        </html>
        """
        mock_get.return_value = mock_response

        url = "https://t.me/channel/123"
        info = TelegramExtractor.extract(url)

        self.assertIsNotNone(info)
        self.assertEqual(info["title"], "Test Video Title")
        self.assertEqual(
            info["video_streams"][0]["url"], "https://cdn.telegram.org/file/video.mp4"
        )

    @responses.activate
    def test_download_generic_success(self):
        url = "http://example.com/file.mp4"
        responses.add(
            responses.GET,
            url,
            body=b"0" * 1024,
            stream=True,
            content_type="video/mp4",
            headers={"Content-Length": "1024"},
        )

        mock_hook = MagicMock()
        item = {}

        download_generic(url, ".", "test_download.mp4", mock_hook, item)

        self.assertTrue(os.path.exists("test_download.mp4"))
        os.remove("test_download.mp4")

        # Verify progress hook called
        self.assertTrue(mock_hook.called)


if __name__ == "__main__":
    unittest.main()
