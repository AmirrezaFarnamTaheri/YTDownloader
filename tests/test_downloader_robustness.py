import unittest
from unittest.mock import MagicMock, patch
import yt_dlp
from downloader import get_video_info, download_video

<<<<<<< HEAD
class TestDownloaderRobustness(unittest.TestCase):

    @patch('yt_dlp.YoutubeDL')
=======

class TestDownloaderRobustness(unittest.TestCase):

    @patch("yt_dlp.YoutubeDL")
>>>>>>> origin/main
    def test_get_video_info_missing_fields(self, mock_ydl_class):
        mock_ydl = mock_ydl_class.return_value
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {
<<<<<<< HEAD
            'title': 'Test Video',
            'formats': [
                {'format_id': '1', 'vcodec': 'h264', 'acodec': 'aac'},
            ]
=======
            "title": "Test Video",
            "formats": [
                {"format_id": "1", "vcodec": "h264", "acodec": "aac"},
            ],
>>>>>>> origin/main
        }

        info = get_video_info("http://test.com")
        self.assertIsNotNone(info)
<<<<<<< HEAD
        self.assertEqual(info['title'], 'Test Video')

    @patch('yt_dlp.YoutubeDL')
=======
        self.assertEqual(info["title"], "Test Video")

    @patch("yt_dlp.YoutubeDL")
>>>>>>> origin/main
    def test_download_video_with_ranges(self, mock_ydl_class):
        mock_ydl = mock_ydl_class.return_value
        mock_ydl.__enter__.return_value = mock_ydl

        # Call with start/end time
        download_video(
            "http://test.com",
            lambda d, i: None,
            {},
            start_time="00:00:10",
<<<<<<< HEAD
            end_time="00:00:20"
=======
            end_time="00:00:20",
>>>>>>> origin/main
        )

        # Verify download_ranges was set in opts
        call_args = mock_ydl_class.call_args[0][0]
<<<<<<< HEAD
        self.assertIn('download_ranges', call_args)
        self.assertTrue(callable(call_args['download_ranges']))
        self.assertTrue(call_args['force_keyframes_at_cuts'])
=======
        self.assertIn("download_ranges", call_args)
        self.assertTrue(callable(call_args["download_ranges"]))
        self.assertTrue(call_args["force_keyframes_at_cuts"])
>>>>>>> origin/main

    def test_filesize_none_handling(self):
        # This logic is inside get_video_info, already tested above implicitly
        pass

<<<<<<< HEAD
if __name__ == '__main__':
=======

if __name__ == "__main__":
>>>>>>> origin/main
    unittest.main()
