import unittest
from unittest.mock import MagicMock, patch, ANY
import yt_dlp
from downloader import get_video_info, download_video


class TestDownloaderCoverage(unittest.TestCase):

    @patch("downloader.TelegramExtractor.is_telegram_url")
    @patch("downloader.TelegramExtractor.extract")
    def test_get_video_info_telegram(self, mock_extract, mock_is_telegram):
        mock_is_telegram.return_value = True
        mock_extract.return_value = {"title": "Telegram Video"}

        info = get_video_info("https://t.me/video")

        self.assertEqual(info["title"], "Telegram Video")
        mock_extract.assert_called_once()

    @patch("downloader.TelegramExtractor.is_telegram_url")
    @patch("yt_dlp.YoutubeDL")
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
        with patch("downloader.GenericExtractor.extract") as mock_generic_extract:
            mock_generic_extract.return_value = {
                "title": "Generic Extracted",
                "video_streams": [{"url": "http"}],
            }

            info = get_video_info("http://generic.link")

            self.assertEqual(info["title"], "Generic Extracted")
            mock_generic_extract.assert_called_once()

    @patch("downloader.TelegramExtractor.is_telegram_url")
    @patch("yt_dlp.YoutubeDL")
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
        # Let's verify if 'en (Auto)' is expected.
        # Code: auto_lang = f"{lang} (Auto)" if lang not in subtitles else lang
        # Since 'en' is in subtitles (from manual), auto_lang becomes 'en'.
        # So 'en' in subtitles is updated with auto captions format? No.
        # if formats: subtitles[auto_lang] = formats
        # So it overwrites 'en' with auto captions if 'en' exists?
        # That seems like a potential bug or feature, but for test we assert what logic does.
        # Since 'en' is in subtitles, auto_lang is 'en'.
        # So it updates subtitles['en'].
        # Thus 'en (Auto)' should NOT be there.
        self.assertNotIn("en (Auto)", info["subtitles"])

    @patch("downloader.TelegramExtractor.is_telegram_url")
    @patch("yt_dlp.YoutubeDL")
    def test_get_video_info_exception_handling(self, MockYDL, mock_is_telegram):
        mock_is_telegram.return_value = False
        mock_ydl = MockYDL.return_value
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("General Error")

        info = get_video_info("http://error.link")
        self.assertIsNone(info)

    @patch("downloader.TelegramExtractor.is_telegram_url")
    @patch("yt_dlp.YoutubeDL")
    def test_get_video_info_ytdlp_error_generic_fallback(
        self, MockYDL, mock_is_telegram
    ):
        mock_is_telegram.return_value = False
        mock_ydl = MockYDL.return_value
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("yt-dlp failed")

        with patch("downloader.GenericExtractor.extract") as mock_generic_extract:
            mock_generic_extract.return_value = {"title": "Fallback"}

            info = get_video_info("http://fallback.link")
            self.assertEqual(info["title"], "Fallback")

    # --- download_video tests ---

    @patch("downloader.TelegramExtractor.is_telegram_url")
    @patch("downloader.TelegramExtractor.extract")
    @patch("downloader.download_generic")
    def test_download_video_telegram(
        self, mock_download_generic, mock_extract, mock_is_telegram
    ):
        mock_is_telegram.return_value = True
        mock_extract.return_value = {
            "title": "Tele",
            "video_streams": [{"url": "direct", "ext": "mp4"}],
        }

        download_video("http://t.me/1", MagicMock(), {}, output_path=".")

        mock_download_generic.assert_called_with(
            "direct", ".", "Tele.mp4", ANY, ANY, ANY
        )

    @patch("downloader.TelegramExtractor.is_telegram_url")
    @patch("downloader.GenericExtractor.extract")
    @patch("downloader.download_generic")
    def test_download_video_force_generic(
        self, mock_download_generic, mock_extract, mock_is_telegram
    ):
        mock_is_telegram.return_value = False
        mock_extract.return_value = {
            "title": "Forced",
            "video_streams": [{"url": "direct", "ext": "mp4"}],
        }

        download_video("http://forced.link", MagicMock(), {}, force_generic=True)

        mock_download_generic.assert_called_with(
            "direct", ".", "Forced.mp4", ANY, ANY, ANY
        )

    @patch("downloader.TelegramExtractor.is_telegram_url")
    @patch("yt_dlp.YoutubeDL")
    def test_download_video_options_time_range(self, MockYDL, mock_is_telegram):
        mock_is_telegram.return_value = False
        mock_ydl = MockYDL.return_value
        mock_ydl.__enter__.return_value = mock_ydl

        download_video(
            "http://yt.link", MagicMock(), {}, start_time="00:01", end_time="00:05"
        )

        args, kwargs = MockYDL.call_args
        opts = args[0]
        self.assertIn("download_ranges", opts)
        self.assertTrue(opts["force_keyframes_at_cuts"])

    @patch("downloader.TelegramExtractor.is_telegram_url")
    @patch("yt_dlp.YoutubeDL")
    def test_download_video_options_gpu_accel(self, MockYDL, mock_is_telegram):
        mock_is_telegram.return_value = False

        download_video("http://yt.link", MagicMock(), {}, gpu_accel="cuda")

        args, kwargs = MockYDL.call_args
        opts = args[0]
        self.assertIn("postprocessor_args", opts)
        self.assertIn("ffmpeg", opts["postprocessor_args"])

    @patch("downloader.TelegramExtractor.is_telegram_url")
    @patch("yt_dlp.YoutubeDL")
    @patch("downloader.GenericExtractor.extract")
    @patch("downloader.download_generic")
    def test_download_video_ytdlp_fail_fallback_generic(
        self, mock_download_generic, mock_extract, MockYDL, mock_is_telegram
    ):
        mock_is_telegram.return_value = False
        mock_ydl = MockYDL.return_value
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.download.side_effect = yt_dlp.utils.DownloadError("Fail")

        mock_extract.return_value = {
            "title": "Fallback",
            "video_streams": [{"url": "direct", "ext": "mp4"}],
        }

        download_video("http://fail.link", MagicMock(), {})

        mock_download_generic.assert_called()

    @patch("downloader.TelegramExtractor.is_telegram_url")
    @patch("yt_dlp.YoutubeDL")
    def test_download_video_cancel_token(self, MockYDL, mock_is_telegram):
        mock_is_telegram.return_value = False
        mock_token = MagicMock()

        download_video("http://yt.link", MagicMock(), {}, cancel_token=mock_token)

        args, kwargs = MockYDL.call_args
        opts = args[0]
        # Progress hook list should have 2 items: 1 default, 1 for cancel check
        self.assertEqual(len(opts["progress_hooks"]), 2)
