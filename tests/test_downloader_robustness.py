import unittest
from unittest.mock import MagicMock, patch
import yt_dlp
from downloader import get_video_info, download_video

class TestDownloaderRobustness(unittest.TestCase):

    @patch("yt_dlp.YoutubeDL")
    def test_get_video_info_missing_fields(self, mock_ydl_class):
        mock_ydl = mock_ydl_class.return_value
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {
            'title': 'Test Video',
            'formats': [
                {'format_id': '1', 'vcodec': 'h264', 'acodec': 'aac'},
            ]
        }

        info = get_video_info("http://test.com")
        self.assertIsNotNone(info)
        self.assertEqual(info['title'], 'Test Video')

    @patch("yt_dlp.YoutubeDL")
    def test_download_video_with_ranges(self, mock_ydl_class):
        mock_ydl = mock_ydl_class.return_value
        mock_ydl.__enter__.return_value = mock_ydl

        # Call with start/end time
        download_video(
            "http://test.com",
            lambda d, i: None,
            {},
            start_time="00:00:10",
            end_time="00:00:20",
        )

        # Verify download_ranges was set in opts
        call_args = mock_ydl_class.call_args[0][0]
        self.assertIn('download_ranges', call_args)
        self.assertTrue(callable(call_args['download_ranges']))
        self.assertTrue(call_args['force_keyframes_at_cuts'])

    @patch("yt_dlp.YoutubeDL")
    def test_download_video_invalid_ranges(self, mock_ydl_class):
        """Test that invalid time ranges raise a ValueError."""
        # Mock parse_duration inside downloader module context
        with patch('yt_dlp.utils.parse_duration') as mock_parse:
            # Mock values: start=30, end=10 (start > end)
            def side_effect(t):
                if t == "00:00:30": return 30
                if t == "00:00:10": return 10
                return 0
            mock_parse.side_effect = side_effect

            with self.assertRaises(ValueError):
                download_video(
                    "http://test.com",
                    lambda d, i: None,
                    {},
                    start_time="00:00:30",
                    end_time="00:00:10",
                )

if __name__ == "__main__":
    unittest.main()
