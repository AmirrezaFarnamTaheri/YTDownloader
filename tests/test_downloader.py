import unittest
from unittest.mock import patch, MagicMock
from downloader import get_video_info, download_video

class TestDownloader(unittest.TestCase):
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_get_video_info(self, mock_youtube_dl):
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.return_value = {
            'title': 'Test Video',
            'thumbnail': 'test.jpg',
            'duration_string': '10:00',
            'subtitles': {'en': [{'ext': 'srt'}]},
            'formats': [
                {'format_id': '1', 'vcodec': 'avc1', 'resolution': '1920x1080', 'fps': 30, 'acodec': 'mp4a.40.2'},
                {'format_id': '2', 'vcodec': 'none', 'acodec': 'opus', 'abr': 160},
            ],
            'chapters': [{'title': 'Chapter 1'}]
        }

        info = get_video_info('test_url')

        self.assertEqual(info['title'], 'Test Video')
        self.assertEqual(info['thumbnail'], 'test.jpg')
        self.assertEqual(info['duration'], '10:00')
        self.assertEqual(list(info['subtitles'].keys()), ['en'])
        self.assertEqual(len(info['video_streams']), 1)
        self.assertEqual(len(info['audio_streams']), 1)
        self.assertEqual(info['chapters'][0]['title'], 'Chapter 1')

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video(self, mock_youtube_dl):
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        progress_hook = MagicMock()

        download_video(
            url='test_url',
            progress_hook=progress_hook,
            playlist=True,
            video_format='best',
            output_path='/tmp',
            subtitle_lang='en',
            subtitle_format='srt',
            split_chapters=True,
            proxy='test_proxy',
            rate_limit='1M'
        )

        mock_youtube_dl.assert_called_once()
        ydl_opts = mock_youtube_dl.call_args[0][0]

        self.assertEqual(ydl_opts['format'], 'best')
        self.assertTrue(ydl_opts['playlist'])
        self.assertIn('test_proxy', ydl_opts['proxy'])
        self.assertIn('1M', ydl_opts['ratelimit'])
        self.assertTrue(ydl_opts['writesubtitles'])
        self.assertEqual(ydl_opts['subtitleslangs'], ['en'])
        self.assertTrue(ydl_opts['split_chapters'])

        mock_instance.download.assert_called_once_with(['test_url'])

if __name__ == '__main__':
    unittest.main()
