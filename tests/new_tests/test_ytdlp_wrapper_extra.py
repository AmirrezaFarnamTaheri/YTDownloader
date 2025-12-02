"""
Extra coverage tests for YTDLPWrapper.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from yt_dlp.utils import DownloadError

from downloader.engines.ytdlp import YTDLPWrapper


class TestYTDLPWrapperExtra(unittest.TestCase):

    @patch("downloader.engines.ytdlp.yt_dlp.YoutubeDL")
    def test_fallback_filename_already_has_extension(self, mock_ydl):
        """Test simple download success path."""
        wrapper = YTDLPWrapper({})

        # Mock YDL instance
        mock_instance = mock_ydl.return_value.__enter__.return_value

        # Configure extract_info result
        mock_instance.extract_info.return_value = {
            "title": "video",
            "ext": "mp4",
            # YTDLPWrapper uses os.path.basename(ydl.prepare_filename(info))
        }

        # Mock prepare_filename
        # YTDLPWrapper calls ydl.prepare_filename(info)
        mock_instance.prepare_filename.return_value = "/tmp/video.mp4"

        info = wrapper.download("http://url")
        self.assertEqual(info["filename"], "video.mp4")
        self.assertEqual(info["filepath"], "/tmp/video.mp4")
