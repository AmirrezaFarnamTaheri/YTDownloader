"""
Tests for downloader.core module coverage.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from downloader.core import download_video
from downloader.types import DownloadOptions


class TestDownloaderCoreCoverage(unittest.TestCase):

    @pytest.fixture(autouse=True)
    def _setup_hooks(self):
        self.hook = MagicMock()
        self.item = {}
        return self.hook, self.item

    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.GenericDownloader.download")
    def test_force_generic_success(self, mock_download, mock_mkdir):
        # Mock what download returns
        mock_download.return_value = {
            "filename": "TestVideo.mp4",
            "filepath": "/tmp/TestVideo.mp4",
            "url": "http://test.com/v.mp4",
        }

        options = DownloadOptions(
            url="http://test.com",
            output_path="/tmp",
            progress_hook=self.hook,
            force_generic=True,
        )
        download_video(options)

        mock_download.assert_called()

    @patch("shutil.which")
    @patch("downloader.core.state")
    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper")
    def test_all_options(self, MockWrapper, mock_mkdir, mock_state, mock_which):
        mock_instance = MockWrapper.return_value
        # Mock FFmpeg availability
        mock_state.ffmpeg_available = True
        # Mock aria2c availability
        mock_which.return_value = "/usr/bin/aria2c"

        options = DownloadOptions(
            url="http://yt.com",
            output_path="/tmp",
            progress_hook=self.hook,
            playlist=True,
            output_template="%(title)s.%(ext)s",
            use_aria2c=True,
            sponsorblock=True,
            gpu_accel="cuda",
            start_time="00:00:10",
            end_time="00:00:20",
            cookies_from_browser="chrome",
        )
        download_video(options)

        args, kwargs = MockWrapper.call_args
        opts = args[0]

        self.assertIn("download_ranges", opts)
        self.assertIn("postprocessor_args", opts)
        self.assertEqual(opts["external_downloader"], "aria2c")
        self.assertFalse(opts["noplaylist"])

    @patch("downloader.core.state")
    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper")
    def test_time_range_success(self, MockWrapper, mock_mkdir, mock_state):
        mock_instance = MockWrapper.return_value
        mock_state.ffmpeg_available = True

        options = DownloadOptions(
            url="http://yt.com",
            progress_hook=self.hook,
            start_time="00:00:10",
            end_time="00:00:20",
        )
        download_video(options)

        args, kwargs = MockWrapper.call_args
        opts = args[0]
        self.assertIn("download_ranges", opts)

    @patch("downloader.core.state")
    @patch("pathlib.Path.mkdir")
    @patch("downloader.core.YTDLPWrapper")
    def test_gpu_accel_vulkan(self, MockWrapper, mock_mkdir, mock_state):
        mock_instance = MockWrapper.return_value
        mock_state.ffmpeg_available = True

        options = DownloadOptions(url="u", progress_hook=self.hook, gpu_accel="vulkan")
        download_video(options)

        args, kwargs = MockWrapper.call_args
        opts = args[0]
        # Should be passed as -hwaccel vulkan
        self.assertIn("-hwaccel", opts["postprocessor_args"]["ffmpeg"])
        self.assertIn("vulkan", opts["postprocessor_args"]["ffmpeg"])

    def test_invalid_time_range(self):
        options = DownloadOptions(
            url="u", start_time="00:00:20", end_time="00:00:10"  # Start > End
        )
        with self.assertRaises(ValueError):
            download_video(options)

    def test_negative_time(self):
        options = DownloadOptions(url="u", start_time="-5")
        with self.assertRaises(ValueError):
            download_video(options)

    def test_invalid_proxy(self):
        options = DownloadOptions(url="u", proxy="ftp://proxy")
        with self.assertRaises(ValueError):
            download_video(options)
