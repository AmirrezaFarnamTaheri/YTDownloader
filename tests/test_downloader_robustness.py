import unittest
from unittest.mock import MagicMock, patch

from downloader.core import download_video
from downloader.info import get_video_info


class TestDownloaderRobustness(unittest.TestCase):

    @patch("yt_dlp.YoutubeDL")
    def test_get_video_info_success(self, mock_ydl):
        mock_instance = mock_ydl.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {
            "title": "Test Video",
            "duration_string": "10:00",
            "thumbnail": "http://thumb.com",
            "formats": [
                {"format_id": "1", "ext": "mp4", "vcodec": "h264", "acodec": "aac"}
            ],
        }

        info = get_video_info("http://youtube.com/watch?v=123")
        self.assertIsNotNone(info)
        self.assertEqual(info["title"], "Test Video")

    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_with_ranges(self, mock_wrapper_class):
        # We need to test if the options passed to YTDLPWrapper contain download_ranges

        # Ensure ffmpeg available for ranges
        with patch("downloader.core.state") as mock_state:
            mock_state.ffmpeg_available = True

            # Call with start/end time, using kwargs for clarity
            download_video(
                url="http://test.com",
                progress_hook=lambda d: None,
                download_item={},
                start_time="00:00:10",
                end_time="00:00:20",
            )

            args, kwargs = mock_wrapper_class.call_args
            opts = args[0]
            self.assertIn("download_ranges", opts)

    def test_download_video_invalid_ranges(self):
        """Test that invalid time ranges raise a ValueError."""
        # Mock parse_duration inside downloader module context or core
        # core._parse_time handles HH:MM:SS parsing itself if simple,
        # but yt-dlp parsing is mocked? core uses _parse_time helper.
        # Let's trust _parse_time logic: "00:00:30" -> 30.

        with self.assertRaises(ValueError):
            download_video(
                url="http://test.com",
                progress_hook=lambda d: None,
                download_item={},
                start_time="00:00:30",
                end_time="00:00:10",
            )


if __name__ == "__main__":
    unittest.main()
