import pytest
import os
from unittest.mock import MagicMock, patch, ANY
from downloader.core import download_video
from downloader.extractors.telegram import TelegramExtractor
from downloader.extractors.generic import GenericExtractor
from utils import CancelToken

class TestDownloaderCoreCoverage:

    @pytest.fixture
    def mock_hooks(self):
        return MagicMock(), {}

    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.GenericExtractor.extract")
    @patch("downloader.core.download_generic")
    def test_force_generic_success(self, mock_download, mock_extract, mock_mkdir, mock_hooks):
        hook, item = mock_hooks
        mock_extract.return_value = {
            "video_streams": [{"url": "http://test.com/v.mp4", "ext": "mp4"}],
            "title": "TestVideo"
        }

        download_video(
            "http://test.com", hook, item, force_generic=True, output_path="/tmp"
        )

        mock_download.assert_called_once()
        args, _ = mock_download.call_args
        assert args[0] == "http://test.com/v.mp4"
        assert args[2] == "TestVideo.mp4"

    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.GenericExtractor.extract")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_force_generic_failure_fallback(self, mock_ytdlp, mock_extract, mock_mkdir, mock_hooks):
        hook, item = mock_hooks
        mock_extract.return_value = None # Fail extraction

        download_video(
            "http://test.com", hook, item, force_generic=True
        )

        # Should fall back to yt-dlp
        mock_ytdlp.assert_called_once()

    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.TelegramExtractor.extract")
    @patch("downloader.core.download_generic")
    def test_telegram_download(self, mock_download, mock_extract, mock_mkdir, mock_hooks):
        hook, item = mock_hooks
        item["is_telegram"] = True
        mock_extract.return_value = {
             "video_streams": [{"url": "http://t.me/v.mp4", "ext": "mp4"}],
            "title": "TelVideo"
        }

        download_video("http://t.me/post/1", hook, item)
        mock_download.assert_called_once()

    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.TelegramExtractor.extract")
    def test_telegram_failure(self, mock_extract, mock_mkdir, mock_hooks):
        hook, item = mock_hooks
        item["is_telegram"] = True
        mock_extract.return_value = None

        with pytest.raises(Exception, match="Could not extract Telegram media"):
            download_video("http://t.me/post/1", hook, item)

    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_all_options(self, mock_ytdlp, mock_mkdir, mock_hooks):
        hook, item = mock_hooks

        download_video(
            "http://yt.com", hook, item,
            playlist=True,
            subtitle_lang="en",
            split_chapters=True,
            match_filter="duration > 60",
            output_template="%(title)s.%(ext)s",
            use_aria2c=True,
            add_metadata=True,
            embed_thumbnail=True,
            recode_video="mp4",
            sponsorblock_remove=True,
            gpu_accel="cuda",
            proxy="http://proxy:8080",
            rate_limit="1M",
            cookies_from_browser="chrome",
            cookies_from_browser_profile="Profile 1"
        )

        mock_ytdlp.assert_called_once()
        _, _, _, _, opts, _ = mock_ytdlp.call_args[0]

        assert opts["playlist"] is True
        assert opts["writesubtitles"] is True
        assert opts["split_chapters"] is True
        assert opts["match_filter"] == "duration > 60"
        assert opts["external_downloader"] == "aria2c"
        assert opts["addmetadata"] is True
        assert opts["writethumbnail"] is True
        assert any(p["key"] == "FFmpegVideoConvertor" for p in opts["postprocessors"])
        assert any(p["key"] == "SponsorBlock" for p in opts["postprocessors"])
        assert opts["proxy"] == "http://proxy:8080"
        assert opts["ratelimit"] == "1M"
        assert opts["cookies_from_browser"] == ("chrome", "Profile 1")
        assert "ffmpeg" in opts["postprocessor_args"]

    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_time_range_success(self, mock_ytdlp, mock_mkdir, mock_hooks):
        hook, item = mock_hooks

        download_video(
            "http://yt.com", hook, item,
            start_time="00:00:10",
            end_time="00:00:20"
        )

        mock_ytdlp.assert_called_once()
        opts = mock_ytdlp.call_args[0][4]
        assert "download_ranges" in opts

    @patch("pathlib.Path.mkdir")
    def test_time_range_invalid(self, mock_mkdir, mock_hooks):
        hook, item = mock_hooks

        with pytest.raises(ValueError, match="Start time.*must be before end time"):
             download_video("u", hook, item, start_time="00:00:20", end_time="00:00:10")

        with pytest.raises(ValueError, match="Invalid time range format"):
             download_video("u", hook, item, start_time="invalid", end_time="00:00:10")

    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper.download")
    def test_gpu_accel_vulkan(self, mock_ytdlp, mock_mkdir, mock_hooks):
        hook, item = mock_hooks
        download_video("u", hook, item, gpu_accel="vulkan")
        opts = mock_ytdlp.call_args[0][4]
        assert "h264_vaapi" in opts["postprocessor_args"]["ffmpeg"]

    @patch("pathlib.Path.mkdir")
    def test_rate_limit_invalid(self, mock_mkdir, mock_hooks):
        hook, item = mock_hooks
        with pytest.raises(ValueError, match="Invalid rate limit"):
             download_video("u", hook, item, rate_limit="invalid")
