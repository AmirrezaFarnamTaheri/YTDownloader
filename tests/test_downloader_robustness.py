# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Robustness tests for downloader module.
"""

import unittest
from unittest.mock import MagicMock, patch

from downloader.core import download_video
from downloader.types import DownloadOptions


class TestDownloaderRobustness(unittest.TestCase):

    def test_download_video_invalid_ranges(self):
        """Test that invalid time ranges raise a ValueError."""
        # Use DownloadOptions
        options = DownloadOptions(
            url="http://test.com",
            progress_hook=lambda d: None,
            download_item={},
            start_time="00:00:30",
            end_time="00:00:10",
        )
        with self.assertRaises(ValueError):
            download_video(options)

    @patch("downloader.core.YTDLPWrapper")
    @patch("shutil.which")
    def test_download_video_with_ranges(self, mock_which, mock_wrapper_class):
        # Ensure ffmpeg available for ranges
        mock_which.return_value = "/usr/bin/ffmpeg"

        options = DownloadOptions(
            url="http://test.com",
            progress_hook=lambda d: None,
            download_item={},
            start_time="00:00:10",
            end_time="00:00:20",
        )
        download_video(options)

        # Verify call args on wrapper
        call_args = mock_wrapper_class.call_args[0][0]
        self.assertIn("download_ranges", call_args)
