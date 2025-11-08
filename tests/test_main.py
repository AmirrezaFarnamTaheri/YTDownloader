import unittest
from unittest.mock import patch, MagicMock, call
from main import download_video

class TestYTDownloader(unittest.TestCase):

    @patch('main.yt_dlp.YoutubeDL')
    def test_download_video(self, mock_youtube_dl):
        """
        Tests the download_video function with a mock object.
        """
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance

        # Test with a single video
        download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        mock_youtube_dl.assert_called_with({'format': 'best', 'playlist': False})
        mock_instance.download.assert_called_with(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])

        # Test with a playlist
        download_video("https://www.youtube.com/playlist?list=PLfdtiltiRHWGc_f-80HJJaA5dD-WwVp-9", playlist=True)
        mock_youtube_dl.assert_called_with({'format': 'best', 'playlist': True})
        mock_instance.download.assert_called_with(["https://www.youtube.com/playlist?list=PLfdtiltiRHWGc_f-80HJJaA5dD-WwVp-9"])

        # Test with a specific format
        download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", video_format='mp4')
        mock_youtube_dl.assert_called_with({'format': 'mp4', 'playlist': False})
        mock_instance.download.assert_called_with(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])

if __name__ == '__main__':
    unittest.main()
