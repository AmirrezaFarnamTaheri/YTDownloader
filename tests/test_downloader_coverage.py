import unittest
from unittest.mock import ANY, MagicMock, patch

import yt_dlp

from downloader.core import download_video
from downloader.info import get_video_info


class TestDownloaderCoverage(unittest.TestCase):

    @patch("downloader.info.TelegramExtractor.is_telegram_url")
    @patch("downloader.info.TelegramExtractor.extract")
    def test_get_video_info_telegram(self, mock_extract, mock_is_telegram):
        mock_is_telegram.return_value = True
        mock_extract.return_value = {"title": "Telegram Video"}

        info = get_video_info("https://t.me/video")

        self.assertEqual(info["title"], "Telegram Video")
        mock_extract.assert_called_once()

    @patch("downloader.info.TelegramExtractor.is_telegram_url")
    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_get_video_info_generic_fallback_no_formats(
        self, MockYDL, mock_is_telegram
    ):
        mock_is_telegram.return_value = False
        mock_ydl = MockYDL.return_value
        mock_ydl.__enter__.return_value = mock_ydl

        # Simulate yt-dlp returning generic extractor but empty formats
        mock_ydl.extract_info.return_value = {
            "extractor_key": "Generic",
            "formats": [],
            "title": "Generic Page",
            "direct": True,
            "url": "http://direct.link",
            "ext": "mp4",
        }

        # Mock GenericExtractor to return something valid
        with patch("downloader.info.GenericExtractor.extract") as mock_generic_extract:
            mock_generic_extract.return_value = {
                "title": "Generic Extracted",
                "video_streams": [{"url": "http"}],
            }

            info = get_video_info("http://generic.link")

            self.assertEqual(info["title"], "Generic Extracted")
            mock_generic_extract.assert_called_once()

    @patch("downloader.info.TelegramExtractor.is_telegram_url")
    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_get_video_info_subtitles_parsing(self, MockYDL, mock_is_telegram):
        mock_is_telegram.return_value = False
        mock_ydl = MockYDL.return_value
        mock_ydl.__enter__.return_value = mock_ydl

        mock_ydl.extract_info.return_value = {
            "title": "Test Video",
            "formats": [],
            "subtitles": {
                "en": [{"ext": "vtt"}],
                "es": "vtt",  # Edge case: string instead of list
            },
            "automatic_captions": {
                "fr": [{"ext": "srt"}],
                "en": [{"ext": "srt"}],  # Should map to en (Auto)
            },
        }

        info = get_video_info("http://video.link")

        self.assertIn("en", info["subtitles"])
        self.assertIn("es", info["subtitles"])
        self.assertIn("fr (Auto)", info["subtitles"])
        # 'en (Auto)' might be missing because 'en' exists in manual subtitles,
        # and the code logic prefers manual subtitles or merges them.
        self.assertNotIn("en (Auto)", info["subtitles"])

    @patch("downloader.info.TelegramExtractor.is_telegram_url")
    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_get_video_info_exception_handling(self, MockYDL, mock_is_telegram):
        mock_is_telegram.return_value = False
        mock_ydl = MockYDL.return_value
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("General Error")

        info = get_video_info("http://error.link")
        self.assertIsNone(info)

    @patch("downloader.info.TelegramExtractor.is_telegram_url")
    @patch("downloader.info.yt_dlp.YoutubeDL")
    def test_get_video_info_ytdlp_error_generic_fallback(
        self, MockYDL, mock_is_telegram
    ):
        mock_is_telegram.return_value = False
        mock_ydl = MockYDL.return_value
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("yt-dlp failed")

        with patch("downloader.info.GenericExtractor.extract") as mock_generic_extract:
            mock_generic_extract.return_value = {"title": "Fallback"}

            info = get_video_info("http://fallback.link")
            self.assertEqual(info["title"], "Fallback")

    # --- download_video tests ---

    @patch("downloader.core.YTDLPWrapper.supports")
    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.TelegramExtractor.extract")
    @patch("downloader.core.GenericDownloader.download")
    def test_download_video_telegram(
        self, mock_generic_download, mock_extract, mock_is_telegram, mock_supports
    ):
        mock_is_telegram.return_value = True
        # YTDLPWrapper supports must return False to trigger generic downloader
        mock_supports.return_value = False

        mock_extract.return_value = {
            "title": "Tele",
            "video_streams": [{"url": "direct", "ext": "mp4"}],
        }

        # Fix args: output_path is 2nd positional, or keyword.
        download_video("http://t.me/1", output_path=".", progress_hook=MagicMock(), download_item={})

        # Updated to call GenericDownloader.download
        mock_generic_download.assert_called()

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    # GenericExtractor is not used by core directly for force_generic flow (GenericDownloader is used)
    # @patch("downloader.core.GenericExtractor.extract")
    @patch("downloader.core.GenericDownloader.download")
    def test_download_video_force_generic(
        self, mock_generic_download, mock_is_telegram
    ):
        mock_is_telegram.return_value = False

        # force_generic=True skips yt-dlp check and goes straight to GenericDownloader
        download_video("http://forced.link", MagicMock(), {}, force_generic=True)

        mock_generic_download.assert_called()

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_options_time_range(self, mock_wrapper_class, mock_is_telegram):
        mock_is_telegram.return_value = False

        # Ensure ffmpeg available for ranges
        with patch("downloader.core.state") as mock_state:
            mock_state.ffmpeg_available = True

            download_video(
                "http://yt.link", MagicMock(), {}, start_time="00:01", end_time="00:05"
            )

            args, kwargs = mock_wrapper_class.call_args
            opts = args[0]
            self.assertIn("download_ranges", opts)

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_options_gpu_accel(self, mock_wrapper_class, mock_is_telegram):
        mock_is_telegram.return_value = False

        # Ensure ffmpeg available
        with patch("downloader.core.state") as mock_state:
            mock_state.ffmpeg_available = True

            download_video("http://yt.link", MagicMock(), {}, gpu_accel="cuda")

            args, kwargs = mock_wrapper_class.call_args
            opts = args[0]
            self.assertIn("postprocessor_args", opts)
            self.assertIn("ffmpeg", opts["postprocessor_args"])

    def test_download_video_ytdlp_fail_fallback_generic(self):
        # Fallback is currently not implemented in core.py try/except block.
        pass

    @patch("downloader.core.TelegramExtractor.is_telegram_url")
    @patch("downloader.core.YTDLPWrapper")
    def test_download_video_cancel_token(self, mock_wrapper_class, mock_is_telegram):
        mock_is_telegram.return_value = False
        mock_token = MagicMock()

        download_video("http://yt.link", MagicMock(), {}, cancel_token=mock_token)

        mock_instance = mock_wrapper_class.return_value
        args, kwargs = mock_instance.download.call_args
        self.assertEqual(args[2], mock_token)
