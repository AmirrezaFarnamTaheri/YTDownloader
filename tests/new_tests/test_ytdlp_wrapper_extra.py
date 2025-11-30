import unittest
from unittest.mock import MagicMock, patch

from yt_dlp.utils import DownloadError

from downloader.engines.ytdlp import YTDLPWrapper


class TestYTDLPWrapperExtra(unittest.TestCase):
    @patch("downloader.engines.ytdlp.yt_dlp.YoutubeDL")
    @patch("downloader.engines.ytdlp.GenericExtractor.extract")
    @patch("downloader.engines.ytdlp.download_generic")
    def test_fallback_filename_already_has_extension(
        self, mock_download_generic, mock_extract, mock_ydl
    ):
        """Test fallback when title already has extension."""
        mock_ydl.return_value.__enter__.return_value.download.side_effect = (
            DownloadError("Fail")
        )

        # Setup generic extraction that returns a title WITH extension
        mock_extract.return_value = {
            "title": "video.mp4",
            "video_streams": [{"url": "http://direct", "ext": "mp4"}],
        }

        # Pass empty options dict
        YTDLPWrapper.download("http://url", "/tmp", MagicMock(), {}, {})

        # Verify download_generic called with "video.mp4", not "video.mp4.mp4"
        args, _ = mock_download_generic.call_args
        self.assertEqual(args[2], "video.mp4")


if __name__ == "__main__":
    unittest.main()
