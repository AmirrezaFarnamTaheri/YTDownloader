import unittest
from unittest.mock import MagicMock, patch, ANY
from downloader.engines.ytdlp import YTDLPWrapper
import yt_dlp


class TestYTDLPWrapperCoverage(unittest.TestCase):

    @patch("yt_dlp.YoutubeDL")
    def test_download_success(self, mock_ydl):
        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance

        progress_hook = MagicMock()
        download_item = {}
        options = {}

        YTDLPWrapper.download(
            "http://url", "/tmp", progress_hook, download_item, options
        )

        # options is now copied, so the original options dict is not modified.
        # We must check the arguments passed to YoutubeDL constructor
        mock_ydl.assert_called_once()
        call_args = mock_ydl.call_args[0][0]
        self.assertIn("progress_hooks", call_args)
        self.assertEqual(len(call_args["progress_hooks"]), 1)

        mock_instance.download.assert_called_with(["http://url"])

        # Test hook execution
        # We need to access the hooks from the call_args since they are not in original options
        call_args["progress_hooks"][0]({})
        progress_hook.assert_called_with({}, download_item)

    @patch("yt_dlp.YoutubeDL")
    def test_download_cancel_token(self, mock_ydl):
        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance

        cancel_token = MagicMock()
        options = {}

        YTDLPWrapper.download(
            "http://url", "/tmp", MagicMock(), {}, options, cancel_token
        )

        # Verify cancel hook added in the copy passed to constructor
        mock_ydl.assert_called_once()
        call_args = mock_ydl.call_args[0][0]
        self.assertIn("progress_hooks", call_args)
        self.assertEqual(len(call_args["progress_hooks"]), 2)

        # Execute token check
        # Note: the order of hooks depends on append. check token logic added first or last?
        # In code:
        # 1. hooks = options.copy...
        # 2. if cancel_token: hooks.append(...)
        # 3. hooks.append(lambda d: progress_hook...)
        # So hook 0 is cancel token check (if options was empty initially)

        call_args["progress_hooks"][0]({})
        cancel_token.check.assert_called()

    @patch("yt_dlp.YoutubeDL")
    def test_download_cancelled_exception(self, mock_ydl):
        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.side_effect = yt_dlp.utils.DownloadError(
            "cancelled by user"
        )

        # Should not raise
        YTDLPWrapper.download("http://url", "/tmp", MagicMock(), {}, {})

    @patch("downloader.engines.ytdlp.GenericExtractor.extract")
    @patch("downloader.engines.ytdlp.download_generic")
    @patch("yt_dlp.YoutubeDL")
    def test_fallback_success(self, mock_ydl, mock_download_generic, mock_extract):
        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.side_effect = yt_dlp.utils.DownloadError("Some error")

        mock_extract.return_value = {
            "title": "video",
            "video_streams": [{"url": "http://direct", "ext": "mp4"}],
        }

        YTDLPWrapper.download("http://url", "/tmp", MagicMock(), {}, {})

        mock_download_generic.assert_called()

    @patch("downloader.engines.ytdlp.GenericExtractor.extract")
    @patch("yt_dlp.YoutubeDL")
    def test_fallback_failed(self, mock_ydl, mock_extract):
        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.side_effect = yt_dlp.utils.DownloadError("Some error")

        mock_extract.return_value = None  # No info

        with self.assertRaises(yt_dlp.utils.DownloadError):
            YTDLPWrapper.download("http://url", "/tmp", MagicMock(), {}, {})

    @patch("yt_dlp.YoutubeDL")
    def test_unexpected_error(self, mock_ydl):
        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.side_effect = Exception("Boom")

        with self.assertRaises(Exception):
            YTDLPWrapper.download("http://url", "/tmp", MagicMock(), {}, {})
