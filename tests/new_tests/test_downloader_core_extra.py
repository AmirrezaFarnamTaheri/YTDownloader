import unittest
from unittest.mock import patch, MagicMock
from downloader.core import download_video
from downloader.engines.ytdlp import YTDLPWrapper


class TestDownloaderCoreExtra(unittest.TestCase):
    def test_time_range_validation_negative(self):
        """Test negative time values."""
        with patch("yt_dlp.utils.parse_duration", side_effect=[-10, 20]):
            with self.assertRaises(ValueError) as cm:
                download_video(
                    "http://url", MagicMock(), {}, start_time="-10:00", end_time="00:20"
                )
            self.assertIn("Time values must be non-negative", str(cm.exception))

    @patch("downloader.core.YTDLPWrapper.download")
    def test_proxy_warning(self, mock_download):
        """Test invalid proxy format raises ValueError."""
        with self.assertRaises(ValueError):
            download_video("http://url", MagicMock(), {}, proxy="invalid_proxy_format")

        # Verify it does NOT proceed to download
        mock_download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
