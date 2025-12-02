import unittest
from unittest.mock import MagicMock, patch

from downloader.core import download_video
from downloader.types import DownloadOptions


class TestFeatureVerification(unittest.TestCase):
    @patch("downloader.core.YTDLPWrapper.download")
    def test_downloader_basic_call(self, mock_download):
        """Verify basic call structure."""
        item = {}

        def hook(d, i):
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
    def test_downloader_arguments_partial(self, mock_wrapper_class):
        """Verify that start/end time arguments are passed to yt-dlp."""

        item = {}

        def hook(d):
            pass

        # Ensure ffmpeg available
        with patch("downloader.core.state") as mock_state:
            mock_state.ffmpeg_available = True

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
        mock_which.return_value = "/usr/bin/aria2c"

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
    def test_downloader_arguments_gpu(self, mock_wrapper_class):
        """Verify that GPU arguments are added to postprocessor args."""

        item = {}

        def hook(d):
            pass

        # Ensure ffmpeg available
        with patch("downloader.core.state") as mock_state:
            mock_state.ffmpeg_available = True

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
