import pytest
from unittest.mock import MagicMock, patch, ANY
import os
from downloader.core import download_video
from downloader.engines.ytdlp import YTDLPWrapper
from downloader.types import DownloadOptions


@pytest.fixture
def mock_ytdlp_wrapper():
    with patch("downloader.core.YTDLPWrapper") as mock:
        yield mock


@pytest.fixture
def mock_generic_downloader():
    with patch("downloader.core.GenericDownloader") as mock:
        yield mock


@pytest.fixture
def mock_telegram_extractor():
    with patch("downloader.core.TelegramExtractor") as mock:
        mock.is_telegram_url.return_value = False
        yield mock


@pytest.fixture
def mock_disk_space():
    with patch("downloader.core._check_disk_space", return_value=True) as mock:
        yield mock


@pytest.fixture
def mock_shutil():
    with patch("downloader.core.shutil") as mock:
        mock.which.return_value = "/usr/bin/ffmpeg"
        yield mock


def test_download_video_generic_fallback(
    mock_ytdlp_wrapper,
    mock_generic_downloader,
    mock_telegram_extractor,
    mock_disk_space,
    mock_shutil,
):
    options = MagicMock(spec=DownloadOptions)
    options.url = "http://example.com/file.zip"
    options.output_path = "/tmp"
    options.output_template = "%(title)s.%(ext)s"
    options.force_generic = True

    mock_ytdlp_wrapper.supports.return_value = False

    download_video(options)

    mock_generic_downloader.download.assert_called_once()
    mock_ytdlp_wrapper.assert_not_called()


def test_download_video_ytdlp(
    mock_ytdlp_wrapper,
    mock_generic_downloader,
    mock_telegram_extractor,
    mock_disk_space,
    mock_shutil,
):
    options = MagicMock(spec=DownloadOptions)
    options.url = "http://youtube.com/watch?v=123"
    options.output_path = "/tmp"
    options.output_template = "%(title)s.%(ext)s"
    options.force_generic = False
    options.playlist = False

    mock_ytdlp_wrapper.supports.return_value = True

    download_video(options)

    # Should instantiate wrapper and call download
    mock_ytdlp_wrapper.assert_called_once()
    mock_ytdlp_wrapper.return_value.download.assert_called_once()


def test_ytdlp_wrapper_supports_caching():
    # Clear cache
    YTDLPWrapper._SUPPORT_CACHE = {}

    with patch("yt_dlp.extractor.gen_extractors") as mock_gen:
        mock_ie = MagicMock()
        mock_ie.suitable.return_value = True
        mock_ie.IE_NAME = "Youtube"
        mock_gen.return_value = [mock_ie]

        # First call
        assert YTDLPWrapper.supports("http://yt.com") is True
        assert mock_gen.call_count == 1

        # Second call should use cache
        assert YTDLPWrapper.supports("http://yt.com") is True
        assert mock_gen.call_count == 1


def test_ytdlp_wrapper_download_cancel_token():
    wrapper = YTDLPWrapper({})
    cancel_token = MagicMock()
    cancel_token.is_set.return_value = True

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        # The hook logic is internal, we can test it by running the hook or expecting exception
        # But here we just want to ensure hooks are registered

        wrapper.download("http://url", cancel_token=cancel_token)

        args, kwargs = mock_ydl.call_args
        opts = args[0]
        assert "progress_hooks" in opts
        assert len(opts["progress_hooks"]) >= 1

        # Test the hook logic
        hook = opts["progress_hooks"][0]
        with pytest.raises(InterruptedError):
            hook({})
