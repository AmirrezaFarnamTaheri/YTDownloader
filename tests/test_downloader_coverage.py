"""
Tests for Core Downloader Logic.
"""

import unittest
from unittest.mock import ANY, MagicMock, patch

from downloader.core import download_video
from downloader.types import DownloadOptions


class TestDownloaderCoverage(unittest.TestCase):

    @patch("downloader.core.YTDLPWrapper.supports")
    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.TelegramExtractor.extract")
    @patch("downloader.core.GenericDownloader.download")
    def test_download_video_telegram(
        self, mock_generic_download, mock_extract, mock_is_telegram, mock_supports
    ):
        mock_is_telegram.return_value = True
        mock_supports.return_value = False

        mock_extract.return_value = {
            "title": "Tele",
            "video_streams": [{"url": "direct", "ext": "mp4"}],
        }

        options = DownloadOptions(
            url="http://t.me/1",
            output_path=".",
            progress_hook=MagicMock(),
            download_item={}
        )
        download_video(options)

        mock_is_telegram.assert_called_with("http://t.me/1")
        mock_extract.assert_called()

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    # GenericExtractor is not used by core directly for force_generic flow (GenericDownloader is used)
    # @patch("downloader.core.GenericExtractor.extract")
    @patch("downloader.core.GenericDownloader.download")
    def test_download_video_force_generic(
        self, mock_generic_download, mock_is_telegram
    ):
        mock_is_telegram.return_value = False

        # force_generic=True skips yt-dlp check and goes straight to GenericDownloader
        options = DownloadOptions(
            url="http://forced.link",
            output_path=".",
            force_generic=True
        )
        download_video(options)

        mock_generic_download.assert_called()

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_options_time_range(self, mock_wrapper_class, mock_is_telegram):
        mock_is_telegram.return_value = False

        # Ensure ffmpeg available for ranges
        with patch("downloader.core.state") as mock_state:
            mock_state.ffmpeg_available = True

            options = DownloadOptions(
                url="http://yt.link",
                output_path=".",
                start_time="00:01",
                end_time="00:05"
            )
            download_video(options)

            # Check options passed to wrapper
            call_args = mock_wrapper_class.call_args[0][0]
            self.assertIn("download_ranges", call_args)

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_options_gpu_accel(self, mock_wrapper_class, mock_is_telegram):
        mock_is_telegram.return_value = False

        # Ensure ffmpeg available
        with patch("downloader.core.state") as mock_state:
            mock_state.ffmpeg_available = True

            options = DownloadOptions(
                url="http://yt.link",
                output_path=".",
                gpu_accel="cuda"
            )
            download_video(options)

            call_args = mock_wrapper_class.call_args[0][0]
            self.assertIn("postprocessor_args", call_args)
            self.assertEqual(call_args["postprocessor_args"]["ffmpeg"][1], "cuda")

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_cancel_token(self, mock_wrapper_class, mock_is_telegram):
        mock_is_telegram.return_value = False
        mock_token = MagicMock()

        options = DownloadOptions(
            url="http://yt.link",
            output_path=".",
            cancel_token=mock_token
        )
        download_video(options)

        # Verify wrapper called with token
        instance = mock_wrapper_class.return_value
        instance.download.assert_called_with(
            "http://yt.link",
            None,
            mock_token,
            download_item=None,
            output_path=ANY
        )

    def test_download_video_validation_fail(self):
        # Invalid time
        options = DownloadOptions(
            url="http://valid.com",
            start_time="-1"
        )
        with self.assertRaises(ValueError):
            download_video(options)

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_yt_dlp_success(self, mock_wrapper_class, mock_is_telegram):
        mock_is_telegram.return_value = False

        options = DownloadOptions(url="http://yt.link")
        download_video(options)

        mock_wrapper_class.assert_called()
        mock_wrapper_class.return_value.download.assert_called()

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_no_ffmpeg(self, mock_wrapper_class, mock_is_telegram):
        mock_is_telegram.return_value = False

        with patch("downloader.core.state") as mock_state:
            mock_state.ffmpeg_available = False

            options = DownloadOptions(url="http://yt.link", video_format="audio")
            download_video(options)

            # Should have disabled postprocessors or merging
            call_args = mock_wrapper_class.call_args[0][0]
            # When format is audio but no ffmpeg, it sets format to bestaudio/best
            self.assertEqual(call_args["format"], "bestaudio/best")
            # And potentially clears postprocessors or sets generic
            # Code: if not ffmpeg ... ydl_opts["postprocessors"] = []
            self.assertEqual(call_args.get("postprocessors"), [])

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_aria2c(self, mock_wrapper_class, mock_is_telegram):
        mock_is_telegram.return_value = False

        with patch("shutil.which", return_value="/usr/bin/aria2c"):
            options = DownloadOptions(url="http://yt.link", use_aria2c=True)
            download_video(options)

            call_args = mock_wrapper_class.call_args[0][0]
            self.assertEqual(call_args.get("external_downloader"), "aria2c")

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_cookies(self, mock_wrapper_class, mock_is_telegram):
        mock_is_telegram.return_value = False

        options = DownloadOptions(url="http://yt.link", cookies_from_browser="chrome")
        download_video(options)

        call_args = mock_wrapper_class.call_args[0][0]
        self.assertEqual(call_args.get("cookiesfrombrowser"), ("chrome",))

    def test_parse_time_logic(self):
        # We can test the helper directly via DownloadOptions static method if we exposed it
        # or just via validation failure
        pass
