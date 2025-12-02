"""
Test coverage for DownloadView.
"""

from unittest.mock import MagicMock, patch

import flet as ft
import pytest

from app_state import AppState
from views.download_view import DownloadView


def test_download_view_advanced_interactions():
    """Test interactions with advanced options."""
    # Setup mocks
    mock_fetch = MagicMock()
    mock_add = MagicMock()
    mock_batch = MagicMock()
    mock_schedule = MagicMock()
    mock_state = MagicMock()

    view = DownloadView(mock_fetch, mock_add, mock_batch, mock_schedule, mock_state)
    view.update = MagicMock()

    # Simulate page connection
    view.page = MagicMock()

    # 1. Test Advanced Options Toggle
    # Not needed as it's just scrolling, but we can check if controls exist
    assert view.time_start.disabled is True
    assert view.time_end.disabled is True

    # 2. Test Cookies Selection
    view.cookies_dd.value = "chrome"
    # view.update() # No change handler

    # 3. Test Switches
    view.playlist_cb.value = True
    view.sponsorblock_cb.value = True
    view.force_generic_cb.value = True

    # Simulate Adding with Advanced Options
    view.url_input.value = "http://test.com"
    view.video_format_dd.value = "best"

    view._on_add_click(None)

    mock_add.assert_called_once()
    args = mock_add.call_args[0][0]
    assert args["cookies_from_browser"] == "chrome"
    assert args["playlist"] is True
    assert args["sponsorblock"] is True
    assert args["force_generic"] is True


def test_download_view_open_download_folder_error():
    """Test error handling when opening download folder."""
    mock_fetch = MagicMock()
    mock_add = MagicMock()
    mock_batch = MagicMock()
    mock_schedule = MagicMock()
    mock_state = MagicMock()

    view = DownloadView(mock_fetch, mock_add, mock_batch, mock_schedule, mock_state)
    view.page = MagicMock()

    # Patch ui_utils.open_folder instead of views.download_view.open_folder
    # because it's imported locally inside the method
    with patch("ui_utils.open_folder", side_effect=Exception("Folder Error")):
        view._open_downloads_folder()  # Correct method name
        # We assert log error via logger but simplified here just ensuring no crash


def test_download_view_update_info_empty():
    """Test update_info with empty data."""
    mock_fetch = MagicMock()
    mock_add = MagicMock()
    mock_batch = MagicMock()
    mock_schedule = MagicMock()
    mock_state = MagicMock()

    view = DownloadView(mock_fetch, mock_add, mock_batch, mock_schedule, mock_state)
    view.update = MagicMock()

    view.update_info(None)

    assert view.add_btn.disabled is True
    assert view.preview_card.visible is False
    assert view.audio_format_dd.visible is False


def test_download_view_update_info_full():
    """Test update_info with complex data."""
    mock_fetch = MagicMock()
    mock_add = MagicMock()
    mock_batch = MagicMock()
    mock_schedule = MagicMock()
    mock_state = MagicMock()

    view = DownloadView(mock_fetch, mock_add, mock_batch, mock_schedule, mock_state)
    view.update = MagicMock()
    # Mock preview card update to prevent "not added to page" error
    view.preview_card.update = MagicMock()

    info = {
        "title": "Test Video",
        "duration": "10:00",
        "thumbnail": "http://img.com",
        "video_streams": [
            {
                "format_id": "137",
                "resolution": "1080p",
                "ext": "mp4",
                "filesize_str": "10.00 MB",  # Added filesize_str to mock
            },
            {
                "format_id": "22",
                "resolution": "720p",
                "ext": "mp4",
                "filesize_str": "5.00 MB",
            },
        ],
        "audio_streams": [
            {"format_id": "140", "abr": "128", "ext": "m4a"},
        ],
    }

    view.update_info(info)

    assert len(view.video_format_dd.options) == 2
    assert "10.00 MB" in view.video_format_dd.options[0].text
    assert view.audio_format_dd.visible is True
    assert len(view.audio_format_dd.options) == 1
