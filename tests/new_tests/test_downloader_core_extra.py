"""
Extra coverage tests for downloader.core.
"""

import unittest
from unittest.mock import MagicMock, patch

from downloader.core import download_video
from downloader.types import DownloadOptions


class TestDownloaderCoreExtra(unittest.TestCase):

    def test_time_range_validation_negative(self):
        """Test negative time values."""
        # Using _parse_time in types.py logic indirectly via validate
        # Or mock it if needed, but integration is better.
        options = DownloadOptions(
            url="http://url", start_time="-10:00", end_time="00:20"
        )

        # DownloadOptions.validate uses _parse_time which returns 0.0 on error?
        # No, _parse_time("-10:00") -> -10.0 * 60??
        # int("-10") works.
        # So it returns negative float.
        # validate checks < 0.

        with self.assertRaises(ValueError) as cm:
            download_video(options)
        self.assertIn("non-negative", str(cm.exception))

    @patch("downloader.core.YTDLPWrapper.download")
    def test_proxy_warning(self, mock_download):
        """Test invalid proxy format raises ValueError."""
        options = DownloadOptions(url="http://url", proxy="invalid_proxy_format")
        with self.assertRaises(ValueError):
            download_video(options)
