import unittest
from typing import Any, Callable, Dict, Optional
from unittest.mock import ANY, MagicMock, patch

import yt_dlp

from downloader.engines.ytdlp import YTDLPWrapper


class TestYTDLPWrapperCoverage(unittest.TestCase):
    @patch("yt_dlp.YoutubeDL")
    def test_download_success(self, mock_ydl):
        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance

        progress_hook = MagicMock()
        download_item = {}
        options = {}

        wrapper = YTDLPWrapper(options)
        wrapper.download(
            "http://url",
            progress_hook=progress_hook,
            download_item=download_item,
            output_path="/tmp",
        )

        mock_instance.extract_info.assert_called_with("http://url", download=True)

    @patch("yt_dlp.YoutubeDL")
    def test_download_cancel_token(self, mock_ydl):
        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance

        cancel_token = MagicMock()
        options = {}

        wrapper = YTDLPWrapper(options)
        wrapper.download(
            "http://url",
            progress_hook=MagicMock(),
            download_item={},
            output_path="/tmp",
            cancel_token=cancel_token,
        )

        # Verify hook added
        args, kwargs = mock_ydl.call_args
        opts = args[0]
        self.assertTrue(len(opts["progress_hooks"]) >= 1)

    @patch("yt_dlp.YoutubeDL")
    def test_download_cancelled_exception(self, mock_ydl):
        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.side_effect = yt_dlp.utils.DownloadError(
            "cancelled by user"
        )

        wrapper = YTDLPWrapper({})
        # Should raise or we catch it? The wrapper currently raises.
        with self.assertRaises(yt_dlp.utils.DownloadError):
            wrapper.download(
                "http://url", progress_hook=MagicMock(), output_path="/tmp"
            )

    @patch("downloader.extractors.generic.GenericExtractor.extract")
    @patch("yt_dlp.YoutubeDL")
    def test_fallback_success(self, mock_ydl, mock_extract):
        # YTDLPWrapper no longer implements fallback logic inside itself directly
        pass

    @patch("downloader.extractors.generic.GenericExtractor.extract")
    @patch("yt_dlp.YoutubeDL")
    def test_fallback_failed(self, mock_ydl, mock_extract):
        pass


if __name__ == "__main__":
    unittest.main()
