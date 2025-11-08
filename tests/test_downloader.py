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
            'subtitles': {'en': [{'ext': 'srt'}]},
            'formats': [
                {'format_id': '1', 'vcodec': 'avc1', 'acodec': 'mp4a', 'ext': 'mp4', 'resolution': '1920x1080', 'fps': 30},
                {'format_id': '2', 'vcodec': 'vp9', 'acodec': 'none', 'ext': 'webm', 'resolution': '3840x2160', 'fps': 60},
                {'format_id': '3', 'vcodec': 'none', 'acodec': 'opus', 'ext': 'webm', 'abr': 160},
            ]
        }
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance

        info = get_video_info('some_url')
        self.assertEqual(info['title'], 'Test Video')
        self.assertEqual(info['thumbnail'], 'http://test.com/thumb.jpg')
        self.assertEqual(info['duration'], '5:00')
        self.assertEqual(info['subtitles'], {'en': ['srt']})
        self.assertEqual(len(info['video_streams']), 2)
        self.assertEqual(info['video_streams'][0]['resolution'], '1920x1080')
        self.assertEqual(info['video_streams'][1]['resolution'], '3840x2160')
        self.assertEqual(len(info['audio_streams']), 1)
        self.assertEqual(info['audio_streams'][0]['abr'], 160)

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

        # Test with chapters
        download_video('some_url', progress_hook, split_chapters=True)
        self.assertTrue(mock_youtube_dl.call_args[0][0]['split_chapters'])
        self.assertIn('section_number', mock_youtube_dl.call_args[0][0]['outtmpl'])

        # Test with proxy and rate limit
        download_video('some_url', progress_hook, proxy='http://proxy.com:8080', rate_limit='1M')
        self.assertEqual(mock_youtube_dl.call_args[0][0]['proxy'], 'http://proxy.com:8080')
        self.assertEqual(mock_youtube_dl.call_args[0][0]['ratelimit'], '1M')

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_with_chapters(self, mock_youtube_dl):
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {
            'chapters': [{'title': 'Chapter 1'}, {'title': 'Chapter 2'}]
        }
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance

        info = get_video_info('some_url')
        self.assertEqual(len(info['chapters']), 2)
        self.assertEqual(info['chapters'][0]['title'], 'Chapter 1')

if __name__ == '__main__':
    unittest.main()
