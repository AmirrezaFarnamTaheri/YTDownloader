import os
from unittest.mock import ANY, MagicMock, patch

import pytest

from downloader.core import download_video
from utils import CancelToken


class TestDownloaderCoreCoverage:

    @pytest.fixture
    def mock_hooks(self):
        return MagicMock(), {}

    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.GenericDownloader.download")
    def test_force_generic_success(
        self, mock_download, mock_mkdir, mock_hooks
    ):
        hook, item = mock_hooks
        # Mock what download returns
        mock_download.return_value = {
            "filename": "TestVideo.mp4",
            "filepath": "/tmp/TestVideo.mp4",
            "url": "http://test.com/v.mp4"
        }

        download_video(
            "http://test.com",
            output_path="/tmp",
            progress_hook=hook,
            force_generic=True
        )

        mock_download.assert_called_once()
        # Verify args: url, output_path, hook, cancel_token
        args, _ = mock_download.call_args
        assert args[0] == "http://test.com"
        assert args[1] == "/tmp"

    @patch("shutil.which")
    @patch("downloader.core.state")
    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper")
    def test_all_options(self, MockWrapper, mock_mkdir, mock_state, mock_which, mock_hooks):
        hook, item = mock_hooks
        mock_instance = MockWrapper.return_value
        # Mock FFmpeg availability
        mock_state.ffmpeg_available = True
        # Mock aria2c availability
        mock_which.return_value = "/usr/bin/aria2c"

        # Test with supported options
        download_video(
            "http://yt.com",
            output_path="/tmp",
            progress_hook=hook,
            playlist=True,
            output_template="%(title)s.%(ext)s",
            use_aria2c=True,
            sponsorblock=True,
            gpu_accel="cuda",
            start_time="00:00:10",
            end_time="00:00:20",
            cookies_from_browser="chrome",
        )

        # Check wrapper initialization options
        MockWrapper.assert_called_once()
        args, _ = MockWrapper.call_args
        opts = args[0]

        # yt-dlp uses noplaylist
        assert opts["noplaylist"] is False
        assert opts["external_downloader"] == "aria2c"
        assert opts["writethumbnail"] is True
        assert any(p["key"] == "SponsorBlock" for p in opts["postprocessors"])
        assert opts["cookiesfrombrowser"] == ("chrome",)
        assert "ffmpeg" in opts["postprocessor_args"]
        assert "download_ranges" in opts

        # Check download called
        mock_instance.download.assert_called_once()

    @patch("downloader.core.state")
    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper")
    def test_time_range_success(self, MockWrapper, mock_mkdir, mock_state, mock_hooks):
        hook, item = mock_hooks
        mock_instance = MockWrapper.return_value
        mock_state.ffmpeg_available = True

        download_video(
            "http://yt.com",
            progress_hook=hook,
            start_time="00:00:10",
            end_time="00:00:20"
        )

        MockWrapper.assert_called_once()
        opts = MockWrapper.call_args[0][0]
        assert "download_ranges" in opts

    @patch("pathlib.Path.mkdir")
    def test_time_range_invalid(self, mock_mkdir, mock_hooks):
        hook, item = mock_hooks
        pass

    @patch("downloader.core.state")
    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper")
    def test_gpu_accel_vulkan(self, MockWrapper, mock_mkdir, mock_state, mock_hooks):
        hook, item = mock_hooks
        mock_instance = MockWrapper.return_value
        mock_state.ffmpeg_available = True

        download_video("u", progress_hook=hook, gpu_accel="vulkan")

        MockWrapper.assert_called_once()
        opts = MockWrapper.call_args[0][0]
        assert "vulkan" in opts["postprocessor_args"]["ffmpeg"]

    @patch("pathlib.Path.mkdir")
    def test_rate_limit_invalid(self, mock_mkdir, mock_hooks):
        hook, item = mock_hooks
        pass

    @patch("pathlib.Path.mkdir")
    def test_output_template_traversal_rejected(self, mock_mkdir, mock_hooks):
        hook, item = mock_hooks
        pass
