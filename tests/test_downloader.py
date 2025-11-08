import unittest
from unittest.mock import patch, MagicMock
from downloader import download_video, get_video_info

class TestDownloader(unittest.TestCase):

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_get_video_info(self, mock_youtube_dl):
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {
            'title': 'Test Video',
            'thumbnail': 'http://test.com/thumb.jpg',
            'duration_string': '5:00',
            'subtitles': {'en': [{'ext': 'srt'}]}
        }
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance

        info = get_video_info('some_url')
        self.assertEqual(info['title'], 'Test Video')
        self.assertEqual(info['thumbnail'], 'http://test.com/thumb.jpg')
        self.assertEqual(info['duration'], '5:00')
        self.assertEqual(info['subtitles'], {'en': ['srt']})

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video(self, mock_youtube_dl):
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        progress_hook = MagicMock()

        # Test basic download
        download_video('some_url', progress_hook)
        mock_instance.download.assert_called_with(['some_url'])
        self.assertIn('progress_hooks', mock_youtube_dl.call_args[0][0])

        # Test with subtitles
        download_video('some_url', progress_hook, subtitle_lang='en', subtitle_format='vtt')
        self.assertTrue(mock_youtube_dl.call_args[0][0]['writesubtitles'])
        self.assertEqual(mock_youtube_dl.call_args[0][0]['subtitleslangs'], ['en'])
        self.assertEqual(mock_youtube_dl.call_args[0][0]['subtitlesformat'], 'vtt')

if __name__ == '__main__':
    unittest.main()
