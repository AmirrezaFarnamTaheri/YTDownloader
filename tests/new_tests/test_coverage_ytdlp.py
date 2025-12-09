import unittest
from unittest.mock import MagicMock, patch
from downloader.engines.ytdlp import YTDLPWrapper
import yt_dlp


class TestYTDLPWrapper(unittest.TestCase):
    def setUp(self):
        self.wrapper = YTDLPWrapper({"option": "1"})

    def test_supports(self):
        self.assertTrue(YTDLPWrapper.supports("http://any.com"))

    @patch("yt_dlp.YoutubeDL")
    def test_download_success(self, MockYTDL):
        mock_instance = MockYTDL.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {
            "title": "Video",
            "duration": 10,
            "thumbnail": "t",
            "uploader": "u",
        }
        mock_instance.prepare_filename.return_value = "Video.mp4"

        with patch("os.path.basename", side_effect=lambda p: p):
            res = self.wrapper.download("http://url.com")

        self.assertEqual(res["filename"], "Video.mp4")
        self.assertEqual(res["type"], "video")

    @patch("yt_dlp.YoutubeDL")
    def test_download_playlist(self, MockYTDL):
        mock_instance = MockYTDL.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {"title": "PL", "entries": [1, 2, 3]}

        res = self.wrapper.download("http://pl.com")

        self.assertEqual(res["type"], "playlist")
        self.assertEqual(res["entries"], 3)

    @patch("yt_dlp.YoutubeDL")
    def test_download_cancel(self, MockYTDL):
        token = MagicMock()
        token.is_set.return_value = True

        mock_instance = MockYTDL.return_value.__enter__.return_value

        def side_effect(url, download=True):
            call_args = MockYTDL.call_args
            if call_args:
                options = call_args[0][0]
                hooks = options.get("progress_hooks", [])
                for h in hooks:
                    h({})
            return {}

        mock_instance.extract_info.side_effect = side_effect

        with self.assertRaisesRegex(InterruptedError, "Download Cancelled by user"):
            self.wrapper.download("http://url.com", cancel_token=token)

    @patch("yt_dlp.YoutubeDL")
    def test_download_error(self, MockYTDL):
        mock_instance = MockYTDL.return_value.__enter__.return_value
        mock_instance.extract_info.side_effect = Exception("General Error")

        with self.assertRaisesRegex(Exception, "General Error"):
            self.wrapper.download("http://url.com")

    @patch("yt_dlp.YoutubeDL")
    def test_download_no_info(self, MockYTDL):
        mock_instance = MockYTDL.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = None

        with self.assertRaisesRegex(Exception, "Failed to extract video info"):
            self.wrapper.download("http://url.com")
