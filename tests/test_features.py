# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
import unittest
from unittest.mock import patch

from downloader.core import download_video
from downloader.types import DownloadOptions


class TestFeatureVerification(unittest.TestCase):
    @patch("downloader.core.YTDLPWrapper.supports", return_value=True)
    @patch("downloader.core.YTDLPWrapper.download")
    def test_downloader_basic_call(self, mock_download, mock_supports):
        """Verify basic call structure."""
        item = {}

        def hook(d):
            """Progress hook that takes 1 argument."""
            pass

        options = DownloadOptions(
            url="http://example.com",
            output_path=".",
            progress_hook=hook,
            download_item=item,
        )
        download_video(options)

        mock_download.assert_called()

    @patch("downloader.core.YTDLPWrapper")
    @patch("shutil.which")
    def test_downloader_arguments_partial(self, mock_which, mock_wrapper_class):
        """Verify that start/end time arguments are passed to yt-dlp."""
        mock_which.return_value = "/usr/bin/ffmpeg"

        item = {}

        def hook(d):
            pass

        options = DownloadOptions(
            url="http://example.com",
            progress_hook=hook,
            download_item=item,
            start_time="00:01:00",
            end_time="00:02:00",
        )
        download_video(options)

        args, kwargs = mock_wrapper_class.call_args
        opts = args[0]
        self.assertIn("download_ranges", opts)

    @patch("downloader.core.YTDLPWrapper")
    @patch("shutil.which")
    def test_downloader_arguments_aria2c(self, mock_which, mock_wrapper_class):
        """Verify that aria2c arguments are passed."""

        # Need mock_which to return valid path for aria2c check
        # But download_video also checks ffmpeg, so we might need side_effect
        def side_effect(cmd):
            if cmd == "aria2c":
                return "/usr/bin/aria2c"
            if cmd == "ffmpeg":
                return "/usr/bin/ffmpeg"
            return None

        mock_which.side_effect = side_effect

        item = {}

        def hook(d):
            pass

        options = DownloadOptions(
            url="http://example.com",
            progress_hook=hook,
            download_item=item,
            use_aria2c=True,
        )
        download_video(options)

        args, kwargs = mock_wrapper_class.call_args
        opts = args[0]
        self.assertEqual(opts["external_downloader"], "aria2c")

    @patch("downloader.core.YTDLPWrapper")
    @patch("shutil.which")
    def test_downloader_arguments_gpu(self, mock_which, mock_wrapper_class):
        """Verify that GPU arguments are added to postprocessor args."""
        mock_which.return_value = "/usr/bin/ffmpeg"

        item = {}

        def hook(d):
            pass

        options = DownloadOptions(
            url="http://example.com",
            progress_hook=hook,
            download_item=item,
            gpu_accel="cuda",
        )
        download_video(options)

        args, kwargs = mock_wrapper_class.call_args
        opts = args[0]
        self.assertIn("-hwaccel", opts["postprocessor_args"]["ffmpeg"])


if __name__ == "__main__":
    unittest.main()
