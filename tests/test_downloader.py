# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Consolidated unit tests for the downloader module.
Covers video info fetching, download configuration, execution logic, and robustness/edge cases.
"""

import unittest
from unittest.mock import ANY, MagicMock, patch

import yt_dlp

from downloader.core import download_video
from downloader.engines.ytdlp import YTDLPWrapper
from downloader.info import get_video_info
from downloader.types import DownloadOptions


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
        # mypy check suppression
        if info:
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
        if info:
            self.assertEqual(info["title"], "No Subtitles Video")
            self.assertEqual(len(info["subtitles"]), 0)

    @patch("downloader.info.GenericExtractor.get_metadata")
    @patch("downloader.info.TelegramExtractor.get_metadata")
    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_get_video_info_download_error(
        self, mock_youtube_dl, mock_tg, mock_generic
    ):
        """Test handling of download errors during info fetching."""
        mock_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.side_effect = yt_dlp.utils.DownloadError(
            "Download failed"
        )

        # Ensure fallbacks return None
        mock_tg.return_value = None
        mock_generic.return_value = None

        info = get_video_info("https://www.youtube.com/watch?v=fail")
        self.assertIsNone(info)


class TestDownloaderOptions(unittest.TestCase):
    """Test cases for DownloadOptions and configuration."""

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    @patch("shutil.which")  # Mock shutil.which for ffmpeg check inside download_video
    @patch("downloader.core._check_disk_space", return_value=True)
    def test_download_video_aria2c(
        self, mock_disk, mock_which, mock_wrapper_class, mock_is_telegram
    ):
        mock_is_telegram.return_value = False
        # Mock aria2c existence
        mock_which.side_effect = lambda x: (
            "/usr/bin/aria2c" if x == "aria2c" else "/usr/bin/ffmpeg"
        )

        options = DownloadOptions(url="http://yt.link", use_aria2c=True)
        download_video(options)

        call_args = mock_wrapper_class.call_args[0][0]
        self.assertEqual(call_args.get("external_downloader"), "aria2c")

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("downloader.core._check_disk_space", return_value=True)
    def test_download_video_cookies(
        self, mock_disk, mock_which, mock_wrapper_class, mock_is_telegram
    ):
        mock_is_telegram.return_value = False

        options = DownloadOptions(url="http://yt.link", cookies_from_browser="chrome")
        download_video(options)

        call_args = mock_wrapper_class.call_args[0][0]
        # yt-dlp expects a 2-tuple: (browser_name, profile_name)
        self.assertEqual(call_args.get("cookiesfrombrowser"), ("chrome", None))

    def test_parse_time_logic(self):
        """Test time parsing via DownloadOptions.get_seconds method."""
        options = DownloadOptions(url="http://example.com")

        # Test MM:SS format
        self.assertEqual(options.get_seconds("01:30"), 90)

        # Test HH:MM:SS format
        self.assertEqual(options.get_seconds("01:00:00"), 3600)

        # Test edge cases
        self.assertEqual(options.get_seconds("00:00"), 0)
        self.assertEqual(options.get_seconds("59:59"), 3599)

        # Test None returns 0
        self.assertEqual(options.get_seconds(None), 0)

        # Test invalid time raises ValueError
        with self.assertRaises(ValueError):
            options.get_seconds("invalid")


class TestDownloaderRobustness(unittest.TestCase):
    """Tests for robustness, edge cases, and error handling."""

    @patch("yt_dlp.YoutubeDL")
    def test_download_video_invalid_args(self, mock_ydl):
        # Invalid url type
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            options = DownloadOptions(url=123)  # type: ignore
            download_video(options)

    @patch("yt_dlp.YoutubeDL")
    @patch("downloader.core._check_disk_space", return_value=True)
    def test_download_video_force_generic(self, mock_disk, mock_ydl):
        # Check if force_generic flag bypasses yt-dlp
        mock_hook = MagicMock()
        item = {}

        with patch("downloader.core.GenericDownloader.download") as mock_download:
            mock_download.return_value = {}  # Return dict
            options = DownloadOptions(
                url="http://url.com",
                progress_hook=mock_hook,
                download_item=item,
                force_generic=True,
            )
            download_video(options)

            mock_download.assert_called()
            mock_ydl.assert_not_called()

    @patch("yt_dlp.YoutubeDL")
    @patch("downloader.core.YTDLPWrapper.supports")
    @patch("downloader.core._check_disk_space", return_value=True)
    def test_download_video_telegram(self, mock_disk, mock_supports, mock_ydl):
        mock_hook = MagicMock()
        item = {}
        mock_supports.return_value = False

        with (
            patch(
                "downloader.core.TelegramExtractor.is_telegram_url", return_value=True
            ),
            patch("downloader.core.TelegramExtractor.extract") as mock_extract,
            patch("downloader.core.GenericDownloader.download"),
        ):

            mock_extract.return_value = {
                "title": "Tel",
                "video_streams": [{"url": "http://t.me/v", "ext": "mp4"}],
            }

            options = DownloadOptions(
                url="https://t.me/123", progress_hook=mock_hook, download_item=item
            )

            download_video(options)

            mock_extract.assert_called()

    @patch("downloader.core.YTDLPWrapper")
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("downloader.core._check_disk_space", return_value=True)
    def test_download_video_exception(self, mock_disk, mock_which, mock_wrapper):
        mock_wrapper.return_value.download.side_effect = RuntimeError(
            "Downloader failed"
        )

        options = DownloadOptions(url="http://fail.com")
        with self.assertRaises(RuntimeError):
            download_video(options)

    def test_download_video_invalid_ranges(self):
        """Test that invalid time ranges raise a ValueError."""
        options = DownloadOptions(
            url="http://test.com",
            progress_hook=lambda d: None,
            download_item={},
            start_time="00:00:30",
            end_time="00:00:10",
        )
        with self.assertRaises(ValueError):
            download_video(options)

    @patch("downloader.core.YTDLPWrapper")
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("downloader.core._check_disk_space", return_value=True)
    def test_download_video_with_ranges(
        self, mock_disk, mock_which, mock_wrapper_class
    ):
        options = DownloadOptions(
            url="http://test.com",
            progress_hook=lambda d: None,
            download_item={},
            start_time="00:00:10",
            end_time="00:00:20",
        )
        download_video(options)

        # Verify call args on wrapper
        call_args = mock_wrapper_class.call_args[0][0]
        self.assertIn("download_ranges", call_args)


class TestDownloaderExecution(unittest.TestCase):
    """Execution flow tests."""

    @patch("downloader.core.YTDLPWrapper")
    @patch("downloader.core.GenericDownloader")
    @patch("downloader.core.TelegramExtractor")
    @patch("downloader.core._check_disk_space", return_value=True)
    @patch("downloader.core.shutil")
    def test_download_video_generic_fallback(
        self,
        mock_shutil,
        mock_disk_space,
        mock_telegram_extractor,
        mock_generic_downloader,
        mock_ytdlp_wrapper,
    ):
        mock_shutil.which.return_value = "/usr/bin/ffmpeg"
        mock_telegram_extractor.is_telegram_url.return_value = False
        mock_generic_downloader.download.return_value = {}

        options = DownloadOptions(
            url="http://example.com/file.zip",
            output_path="/tmp",
            output_template="%(title)s.%(ext)s",
            force_generic=True,
        )

        mock_ytdlp_wrapper.supports.return_value = False

        download_video(options)

        mock_generic_downloader.download.assert_called_once()
        mock_ytdlp_wrapper.assert_not_called()

    @patch("downloader.core.YTDLPWrapper")
    @patch("downloader.core.GenericDownloader")
    @patch("downloader.core.TelegramExtractor")
    @patch("downloader.core._check_disk_space", return_value=True)
    @patch("downloader.core.shutil")
    def test_download_video_ytdlp(
        self,
        mock_shutil,
        mock_disk_space,
        mock_telegram_extractor,
        mock_generic_downloader,
        mock_ytdlp_wrapper,
    ):
        mock_shutil.which.return_value = "/usr/bin/ffmpeg"
        mock_telegram_extractor.is_telegram_url.return_value = False

        options = DownloadOptions(
            url="http://youtube.com/watch?v=123",
            output_path="/tmp",
            output_template="%(title)s.%(ext)s",
            force_generic=False,
            playlist=False,
        )

        mock_ytdlp_wrapper.supports.return_value = True

        download_video(options)

        # Should instantiate wrapper and call download
        mock_ytdlp_wrapper.assert_called_once()
        mock_ytdlp_wrapper.return_value.download.assert_called_once()

    def test_ytdlp_wrapper_supports_caching(self):
        # Clear cache
        YTDLPWrapper._SUPPORT_CACHE = {}

        with patch("yt_dlp.extractor.gen_extractors") as mock_gen:
            mock_ie = MagicMock()
            mock_ie.suitable.return_value = True
            mock_ie.IE_NAME = "Youtube"
            mock_gen.return_value = [mock_ie]

            # First call
            self.assertTrue(YTDLPWrapper.supports("http://yt.com"))
            self.assertEqual(mock_gen.call_count, 1)

            # Second call should use cache
            self.assertTrue(YTDLPWrapper.supports("http://yt.com"))
            self.assertEqual(mock_gen.call_count, 1)

    def test_ytdlp_wrapper_download_cancel_token(self):
        wrapper = YTDLPWrapper({})
        cancel_token = MagicMock()
        cancel_token.is_set.return_value = True

        # Mock CancelToken behavior
        cancel_token.check.side_effect = InterruptedError("Cancelled")

        with patch("yt_dlp.YoutubeDL") as mock_ydl:
            wrapper.download("http://url", cancel_token=cancel_token)

            args, kwargs = mock_ydl.call_args
            opts = args[0]
            self.assertIn("progress_hooks", opts)
            self.assertGreaterEqual(len(opts["progress_hooks"]), 1)

            # Test the hook logic
            hook = opts["progress_hooks"][0]
            with self.assertRaises(InterruptedError):
                hook({})
