"""
Comprehensive unit tests for the downloader module.
Tests cover video info fetching, error handling, and download configuration.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import yt_dlp
from downloader.info import get_video_info
from downloader.core import download_video


class TestGetVideoInfo(unittest.TestCase):
    """Test cases for get_video_info function."""

    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_get_video_info_success(self, mock_youtube_dl):
        """Test successful video info retrieval."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.return_value = {
            "title": "Test Video",
            "thumbnail": "https://example.com/thumb.jpg",
            "duration_string": "10:30",
            "subtitles": {"en": [{"ext": "srt"}], "es": [{"ext": "vtt"}]},
            "formats": [
                {
                    "format_id": "22",
                    "vcodec": "avc1",
                    "acodec": "mp4a.40.2",
                    "resolution": "1920x1080",
                    "fps": 30,
                    "ext": "mp4",
                    "filesize": 1024 * 1024 * 500,
                },
                {
                    "format_id": "140",
                    "vcodec": "none",
                    "acodec": "opus",
                    "abr": 160,
                    "ext": "webm",
                    "filesize": 1024 * 1024 * 50,
                },
            ],
            "chapters": [{"title": "Chapter 1", "start_time": 0}],
        }

        info = get_video_info("https://www.youtube.com/watch?v=test")

        self.assertIsNotNone(info)
        self.assertEqual(info["title"], "Test Video")
        self.assertEqual(info["thumbnail"], "https://example.com/thumb.jpg")
        self.assertEqual(info["duration"], "10:30")
        self.assertEqual(len(info["subtitles"]), 2)
        self.assertIn("en", info["subtitles"])
        self.assertIn("es", info["subtitles"])
        self.assertEqual(len(info["video_streams"]), 1)
        self.assertEqual(len(info["audio_streams"]), 1)
        self.assertEqual(info["video_streams"][0]["format_id"], "22")
        self.assertEqual(info["audio_streams"][0]["format_id"], "140")
        self.assertIsNotNone(info["chapters"])

    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_get_video_info_no_subtitles(self, mock_youtube_dl):
        """Test video info retrieval when no subtitles are available."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.return_value = {
            "title": "No Subtitles Video",
            "thumbnail": None,
            "duration_string": "N/A",
            "subtitles": None,
            "formats": [],
            "chapters": None,
        }

        info = get_video_info("https://www.youtube.com/watch?v=test")

        self.assertIsNotNone(info)
        self.assertEqual(info["title"], "No Subtitles Video")
        self.assertEqual(len(info["subtitles"]), 0)

    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_get_video_info_download_error(self, mock_youtube_dl):
        """Test handling of download errors during info fetching."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.side_effect = yt_dlp.utils.DownloadError(
            "Video not found"
        )

        # We expect None now as per robustness improvements
        result = get_video_info("https://www.youtube.com/watch?v=invalid")
        self.assertIsNone(result)

    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_get_video_info_unexpected_error(self, mock_youtube_dl):
        """Test handling of unexpected errors during info fetching."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.side_effect = Exception("Network error")

        result = get_video_info("https://www.youtube.com/watch?v=test")

        self.assertIsNone(result)

    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_get_video_info_mixed_formats(self, mock_youtube_dl):
        """Test with a mix of video and audio formats."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.return_value = {
            "title": "Mixed Formats Video",
            "thumbnail": None,
            "duration_string": "5:00",
            "subtitles": {},
            "formats": [
                {
                    "format_id": "18",
                    "vcodec": "avc1",
                    "acodec": "aac",
                    "resolution": "360p",
                    "fps": 24,
                    "ext": "mp4",
                    "filesize": None,
                },
                {
                    "format_id": "22",
                    "vcodec": "avc1",
                    "acodec": "aac",
                    "resolution": "720p",
                    "fps": 30,
                    "ext": "mp4",
                    "filesize": 200000000,
                },
                {
                    "format_id": "137",
                    "vcodec": "avc1",
                    "acodec": "none",
                    "resolution": "1080p",
                    "fps": 30,
                    "ext": "mp4",
                    "filesize": 300000000,
                },
                {
                    "format_id": "251",
                    "vcodec": "none",
                    "acodec": "opus",
                    "abr": 160,
                    "ext": "webm",
                    "filesize": 10000000,
                },
                {
                    "format_id": "140",
                    "vcodec": "none",
                    "acodec": "mp4a",
                    "abr": 128,
                    "ext": "m4a",
                    "filesize": 8000000,
                },
            ],
            "chapters": None,
        }

        info = get_video_info("https://www.youtube.com/watch?v=test")

        # Should have formats with audio codec != 'none' and video codec != 'none' in video_streams
        # Should have formats with video codec == 'none' and audio codec != 'none' in audio_streams
        self.assertEqual(len(info["video_streams"]), 3)  # All except audio-only
        self.assertEqual(len(info["audio_streams"]), 2)  # Audio-only formats


class TestDownloadVideo(unittest.TestCase):
    """Test cases for download_video function."""

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_success(self, mock_download, mock_mkdir):
        """Test successful video download."""
        progress_hook = MagicMock()
        download_item = {"url": "https://example.com/video"}

        download_video(
            url="https://www.youtube.com/watch?v=test",
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format="22",
            output_path="/tmp/downloads",
            subtitle_lang=None,
            subtitle_format="srt",
            split_chapters=False,
            proxy=None,
            rate_limit=None,
            cancel_token=None,
        )

        mock_download.assert_called()

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_with_subtitles(self, mock_download, mock_mkdir):
        """Test video download with subtitle options."""
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url="https://www.youtube.com/watch?v=test",
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format="best",
            output_path=".",
            subtitle_lang="en",
            subtitle_format="vtt",
            split_chapters=False,
            proxy=None,
            rate_limit=None,
            cancel_token=None,
        )

        # Get the ydl_opts passed to download
        args, kwargs = mock_download.call_args
        ydl_opts = args[4]  # options is 5th arg
        self.assertTrue(ydl_opts["writesubtitles"])
        self.assertEqual(ydl_opts["subtitleslangs"], ["en"])
        self.assertEqual(ydl_opts["subtitlesformat"], "vtt")

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_with_chapters(self, mock_download, mock_mkdir):
        """Test video download with chapter splitting."""
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url="https://www.youtube.com/watch?v=test",
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format="best",
            output_path="/tmp",
            subtitle_lang=None,
            subtitle_format="srt",
            split_chapters=True,
            proxy=None,
            rate_limit=None,
            cancel_token=None,
        )

        args, kwargs = mock_download.call_args
        ydl_opts = args[4]
        self.assertTrue(ydl_opts["split_chapters"])

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_with_proxy(self, mock_download, mock_mkdir):
        """Test video download with proxy settings."""
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url="https://www.youtube.com/watch?v=test",
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format="best",
            output_path=".",
            subtitle_lang=None,
            subtitle_format="srt",
            split_chapters=False,
            proxy="http://proxy.example.com:8080",
            rate_limit=None,
            cancel_token=None,
        )

        args, kwargs = mock_download.call_args
        ydl_opts = args[4]
        self.assertEqual(ydl_opts["proxy"], "http://proxy.example.com:8080")

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_with_rate_limit(self, mock_download, mock_mkdir):
        """Test video download with rate limiting."""
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url="https://www.youtube.com/watch?v=test",
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format="best",
            output_path=".",
            subtitle_lang=None,
            subtitle_format="srt",
            split_chapters=False,
            proxy=None,
            rate_limit="500K",
            cancel_token=None,
        )

        args, kwargs = mock_download.call_args
        ydl_opts = args[4]
        self.assertEqual(ydl_opts["ratelimit"], "500K")

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_with_cancel_token(self, mock_download, mock_mkdir):
        """Test that cancel token is added to progress hooks."""
        progress_hook = MagicMock()
        download_item = {}
        cancel_token = MagicMock()

        download_video(
            url="https://www.youtube.com/watch?v=test",
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format="best",
            output_path=".",
            subtitle_lang=None,
            subtitle_format="srt",
            split_chapters=False,
            proxy=None,
            rate_limit=None,
            cancel_token=cancel_token,
        )

        args, kwargs = mock_download.call_args
        # YTDLPWrapper.download(url, output_path, hook, item, opts, cancel_token)
        self.assertEqual(args[5], cancel_token)

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_cancelled_by_user(self, mock_download, mock_mkdir):
        """Test graceful handling of user cancellation."""
        mock_download.side_effect = yt_dlp.utils.DownloadError("Cancelled by user")
        progress_hook = MagicMock()
        download_item = {}

        # Should raise because download_video doesn't catch DownloadError from YTDLPWrapper
        # Wait, YTDLPWrapper catches DownloadError?
        # YTDLPWrapper catches DownloadError, logs it, attempts fallback.
        # If "Cancelled by user" is in string, it returns.

        # BUT, here I am mocking YTDLPWrapper.download itself!
        # So I am simulating `YTDLPWrapper.download` raising an exception.
        # `download_video` does NOT catch exceptions from `YTDLPWrapper.download`.
        # So this test expects it to raise.

        with self.assertRaises(yt_dlp.utils.DownloadError):
            download_video(
                url="https://www.youtube.com/watch?v=test",
                progress_hook=progress_hook,
                download_item=download_item,
                playlist=False,
                video_format="best",
                output_path=".",
                subtitle_lang=None,
                subtitle_format="srt",
                split_chapters=False,
                proxy=None,
                rate_limit=None,
                cancel_token=None,
            )

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_error(self, mock_download, mock_mkdir):
        """Test error handling during download."""
        mock_download.side_effect = yt_dlp.utils.DownloadError("Access denied")
        progress_hook = MagicMock()
        download_item = {}

        with self.assertRaises(yt_dlp.utils.DownloadError):
            download_video(
                url="https://www.youtube.com/watch?v=test",
                progress_hook=progress_hook,
                download_item=download_item,
                playlist=False,
                video_format="best",
                output_path=".",
                subtitle_lang=None,
                subtitle_format="srt",
                split_chapters=False,
                proxy=None,
                rate_limit=None,
                cancel_token=None,
            )

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_playlist(self, mock_download, mock_mkdir):
        """Test playlist download configuration."""
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url="https://www.youtube.com/playlist?list=PLtest",
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=True,
            video_format="best",
            output_path=".",
            subtitle_lang=None,
            subtitle_format="srt",
            split_chapters=False,
            proxy=None,
            rate_limit=None,
            cancel_token=None,
        )

        args, kwargs = mock_download.call_args
        ydl_opts = args[4]
        self.assertTrue(ydl_opts["playlist"])

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_creates_output_directory(self, mock_download, mock_mkdir):
        """Test that output directory is created if it doesn't exist."""
        progress_hook = MagicMock()
        download_item = {}

        download_video(
            url="https://www.youtube.com/watch?v=test",
            progress_hook=progress_hook,
            download_item=download_item,
            playlist=False,
            video_format="best",
            output_path="/nonexistent/path",
            subtitle_lang=None,
            subtitle_format="srt",
            split_chapters=False,
            proxy=None,
            rate_limit=None,
            cancel_token=None,
        )

        # mkdir should be called to create the output directory
        mock_mkdir.assert_called()

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_recode(self, mock_download, mock_mkdir):
        download_video(
            url="test",
            progress_hook=lambda d, i: None,
            download_item={},
            recode_video="mp4",
        )

        args, kwargs = mock_download.call_args
        ydl_opts = args[4]
        pps = ydl_opts["postprocessors"]
        self.assertTrue(
            any(
                p["key"] == "FFmpegVideoConvertor" and p["preferredformat"] == "mp4"
                for p in pps
            )
        )

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_sponsorblock(self, mock_download, mock_mkdir):
        download_video(
            url="test",
            progress_hook=lambda d, i: None,
            download_item={},
            sponsorblock_remove=True,
        )

        args, kwargs = mock_download.call_args
        ydl_opts = args[4]
        pps = ydl_opts["postprocessors"]
        self.assertTrue(any(p["key"] == "SponsorBlock" for p in pps))

    @patch("downloader.core.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_download_video_gpu_accel(self, mock_download, mock_mkdir):
        download_video(
            url="test",
            progress_hook=lambda d, i: None,
            download_item={},
            gpu_accel="cuda",
        )

        args, kwargs = mock_download.call_args
        ydl_opts = args[4]
        self.assertIn("postprocessor_args", ydl_opts)
        self.assertIn("h264_nvenc", ydl_opts["postprocessor_args"]["ffmpeg"])


if __name__ == "__main__":
    unittest.main()
