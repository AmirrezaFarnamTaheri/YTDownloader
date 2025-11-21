"""
Comprehensive unit tests for the downloader module.
Tests cover video info fetching, error handling, and download configuration.
"""
import unittest
from unittest.mock import patch, MagicMock, call
import yt_dlp
from downloader import get_video_info, download_video


class TestGetVideoInfo(unittest.TestCase):
    """Test cases for get_video_info function."""

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_success(self, mock_youtube_dl, mock_mkdir=None):
        """Test successful video info retrieval."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.return_value = {
            'title': 'Test Video',
            'thumbnail': 'https://example.com/thumb.jpg',
            'duration_string': '10:30',
            'subtitles': {'en': [{'ext': 'srt'}], 'es': [{'ext': 'vtt'}]},
            'formats': [
                {
                    'format_id': '22',
                    'vcodec': 'avc1',
                    'acodec': 'mp4a.40.2',
                    'resolution': '1920x1080',
                    'fps': 30,
                    'ext': 'mp4',
                    'filesize': 1024 * 1024 * 500,
                },
                {
                    'format_id': '140',
                    'vcodec': 'none',
                    'acodec': 'opus',
                    'abr': 160,
                    'ext': 'webm',
                    'filesize': 1024 * 1024 * 50,
                },
            ],
            'chapters': [{'title': 'Chapter 1', 'start_time': 0}],
        }

        info = get_video_info('https://www.youtube.com/watch?v=test')

        self.assertIsNotNone(info)
        self.assertEqual(info['title'], 'Test Video')
        self.assertEqual(info['thumbnail'], 'https://example.com/thumb.jpg')
        self.assertEqual(info['duration'], '10:30')
        self.assertEqual(len(info['subtitles']), 2)
        self.assertIn('en', info['subtitles'])
        self.assertIn('es', info['subtitles'])
        self.assertEqual(len(info['video_streams']), 1)
        self.assertEqual(len(info['audio_streams']), 1)
        self.assertEqual(info['video_streams'][0]['format_id'], '22')
        self.assertEqual(info['audio_streams'][0]['format_id'], '140')
        self.assertIsNotNone(info['chapters'])

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_no_subtitles(self, mock_youtube_dl):
        """Test video info retrieval when no subtitles are available."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.return_value = {
            'title': 'No Subtitles Video',
            'thumbnail': None,
            'duration_string': 'N/A',
            'subtitles': None,
            'formats': [],
            'chapters': None,
        }

        info = get_video_info('https://www.youtube.com/watch?v=test')

        self.assertIsNotNone(info)
        self.assertEqual(info['title'], 'No Subtitles Video')
        self.assertEqual(len(info['subtitles']), 0)

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_download_error(self, mock_youtube_dl):
        """Test handling of download errors during info fetching."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.side_effect = yt_dlp.utils.DownloadError("Video not found")

        with self.assertRaises(yt_dlp.utils.DownloadError):
            get_video_info('https://www.youtube.com/watch?v=invalid')

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_unexpected_error(self, mock_youtube_dl):
        """Test handling of unexpected errors during info fetching."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.side_effect = Exception("Network error")

        result = get_video_info('https://www.youtube.com/watch?v=test')

        self.assertIsNone(result)

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_mixed_formats(self, mock_youtube_dl):
        """Test with a mix of video and audio formats."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.return_value = {
            'title': 'Mixed Formats Video',
            'thumbnail': None,
            'duration_string': '5:00',
            'subtitles': {},
            'formats': [
                {'format_id': '18', 'vcodec': 'avc1', 'acodec': 'aac', 'resolution': '360p', 'fps': 24, 'ext': 'mp4', 'filesize': None},
                {'format_id': '22', 'vcodec': 'avc1', 'acodec': 'aac', 'resolution': '720p', 'fps': 30, 'ext': 'mp4', 'filesize': 200000000},
                {'format_id': '137', 'vcodec': 'avc1', 'acodec': 'none', 'resolution': '1080p', 'fps': 30, 'ext': 'mp4', 'filesize': 300000000},
                {'format_id': '251', 'vcodec': 'none', 'acodec': 'opus', 'abr': 160, 'ext': 'webm', 'filesize': 10000000},
                {'format_id': '140', 'vcodec': 'none', 'acodec': 'mp4a', 'abr': 128, 'ext': 'm4a', 'filesize': 8000000},
            ],
            'chapters': None,
        }

        info = get_video_info('https://www.youtube.com/watch?v=test')

        # Should have formats with audio codec != 'none' and video codec != 'none' in video_streams
        # Should have formats with video codec == 'none' and audio codec != 'none' in audio_streams
        self.assertEqual(len(info['video_streams']), 3)  # All except audio-only
        self.assertEqual(len(info['audio_streams']), 2)  # Audio-only formats


class TestDownloadVideo(unittest.TestCase):
    """Test cases for download_video function."""

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_success(self, mock_youtube_dl, mock_mkdir):
        """Test successful video download."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        progress_hook = MagicMock()
        download_item = {'url': 'https://example.com/video'}

        download_video(
            url='https://www.youtube.com/watch?v=test',
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format='22',
            output_path='/tmp/downloads',
            subtitle_lang=None,
            subtitle_format='srt',
            split_chapters=False,
            proxy=None,
            rate_limit=None,
            cancel_token=None
        )

        mock_instance.download.assert_called_once_with(['https://www.youtube.com/watch?v=test'])

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_with_subtitles(self, mock_youtube_dl, mock_mkdir):
        """Test video download with subtitle options."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url='https://www.youtube.com/watch?v=test',
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format='best',
            output_path='.',
            subtitle_lang='en',
            subtitle_format='vtt',
            split_chapters=False,
            proxy=None,
            rate_limit=None,
            cancel_token=None
        )

        # Get the ydl_opts passed to YoutubeDL
        ydl_opts = mock_youtube_dl.call_args[0][0]
        self.assertTrue(ydl_opts['writesubtitles'])
        self.assertEqual(ydl_opts['subtitleslangs'], ['en'])
        self.assertEqual(ydl_opts['subtitlesformat'], 'vtt')

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_with_chapters(self, mock_youtube_dl, mock_mkdir):
        """Test video download with chapter splitting."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url='https://www.youtube.com/watch?v=test',
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format='best',
            output_path='/tmp',
            subtitle_lang=None,
            subtitle_format='srt',
            split_chapters=True,
            proxy=None,
            rate_limit=None,
            cancel_token=None
        )

        ydl_opts = mock_youtube_dl.call_args[0][0]
        self.assertTrue(ydl_opts['split_chapters'])

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_with_proxy(self, mock_youtube_dl, mock_mkdir):
        """Test video download with proxy settings."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url='https://www.youtube.com/watch?v=test',
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format='best',
            output_path='.',
            subtitle_lang=None,
            subtitle_format='srt',
            split_chapters=False,
            proxy='http://proxy.example.com:8080',
            rate_limit=None,
            cancel_token=None
        )

        ydl_opts = mock_youtube_dl.call_args[0][0]
        self.assertEqual(ydl_opts['proxy'], 'http://proxy.example.com:8080')

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_with_rate_limit(self, mock_youtube_dl, mock_mkdir):
        """Test video download with rate limiting."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url='https://www.youtube.com/watch?v=test',
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format='best',
            output_path='.',
            subtitle_lang=None,
            subtitle_format='srt',
            split_chapters=False,
            proxy=None,
            rate_limit='500K',
            cancel_token=None
        )

        ydl_opts = mock_youtube_dl.call_args[0][0]
        self.assertEqual(ydl_opts['ratelimit'], '500K')

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_with_cancel_token(self, mock_youtube_dl, mock_mkdir):
        """Test that cancel token is added to progress hooks."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        progress_hook = MagicMock()
        download_item = {}
        cancel_token = MagicMock()

        download_video(
            url='https://www.youtube.com/watch?v=test',
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format='best',
            output_path='.',
            subtitle_lang=None,
            subtitle_format='srt',
            split_chapters=False,
            proxy=None,
            rate_limit=None,
            cancel_token=cancel_token
        )

        ydl_opts = mock_youtube_dl.call_args[0][0]
        # Progress hooks should include the cancel_token check
        self.assertGreaterEqual(len(ydl_opts['progress_hooks']), 2)

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_cancelled_by_user(self, mock_youtube_dl, mock_mkdir):
        """Test graceful handling of user cancellation."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.side_effect = yt_dlp.utils.DownloadError("Cancelled by user")
        progress_hook = MagicMock()
        download_item = {}

        # Should not raise exception
        download_video(
            url='https://www.youtube.com/watch?v=test',
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format='best',
            output_path='.',
            subtitle_lang=None,
            subtitle_format='srt',
            split_chapters=False,
            proxy=None,
            rate_limit=None,
            cancel_token=None
        )

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_error(self, mock_youtube_dl, mock_mkdir):
        """Test error handling during download."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.side_effect = yt_dlp.utils.DownloadError("Access denied")
        progress_hook = MagicMock()
        download_item = {}

        with self.assertRaises(yt_dlp.utils.DownloadError):
            download_video(
                url='https://www.youtube.com/watch?v=test',
                progress_hook=progress_hook,
                download_item=download_item,
                playlist=False,
                video_format='best',
                output_path='.',
                subtitle_lang=None,
                subtitle_format='srt',
                split_chapters=False,
                proxy=None,
                rate_limit=None,
                cancel_token=None
            )

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_playlist(self, mock_youtube_dl, mock_mkdir):
        """Test playlist download configuration."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url='https://www.youtube.com/playlist?list=PLtest',
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=True,
            video_format='best',
            output_path='.',
            subtitle_lang=None,
            subtitle_format='srt',
            split_chapters=False,
            proxy=None,
            rate_limit=None,
            cancel_token=None
        )

        ydl_opts = mock_youtube_dl.call_args[0][0]
        self.assertTrue(ydl_opts['playlist'])

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_creates_output_directory(self, mock_youtube_dl, mock_mkdir):
        """Test that output directory is created if it doesn't exist."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url='https://www.youtube.com/watch?v=test',
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format='best',
            output_path='/nonexistent/path',
            subtitle_lang=None,
            subtitle_format='srt',
            split_chapters=False,
            proxy=None,
            rate_limit=None,
            cancel_token=None
        )

        # mkdir should be called to create the output directory
        mock_mkdir.assert_called()

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_recode(self, mock_youtube_dl, mock_mkdir):
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance

        download_video(
            url='test', progress_hook=lambda d,i: None, download_item={},
            recode_video='mp4'
        )

        ydl_opts = mock_youtube_dl.call_args[0][0]
        pps = ydl_opts['postprocessors']
        self.assertTrue(any(p['key'] == 'FFmpegVideoConvertor' and p['preferedformat'] == 'mp4' for p in pps))

    @patch('downloader.Path.mkdir')
    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_video_sponsorblock(self, mock_youtube_dl, mock_mkdir):
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance

        download_video(
            url='test', progress_hook=lambda d,i: None, download_item={},
            sponsorblock_remove=True
        )

        ydl_opts = mock_youtube_dl.call_args[0][0]
        pps = ydl_opts['postprocessors']
        self.assertTrue(any(p['key'] == 'SponsorBlock' for p in pps))

if __name__ == '__main__':
    unittest.main()
