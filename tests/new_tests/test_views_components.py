import pytest
from unittest.mock import MagicMock, patch
import flet as ft
from views.components.download_input_card import DownloadInputCard
from views.components.history_item import HistoryItemControl


@pytest.fixture
def mock_app_state():
    mock = MagicMock()
    mock.config.get.return_value = None
    return mock


def test_download_input_card_init(mock_app_state):
    card = DownloadInputCard(
        on_fetch=MagicMock(), on_paste=MagicMock(), app_state=mock_app_state
    )
    assert isinstance(card.url_input, ft.TextField)
    assert isinstance(card.fetch_btn, ft.ElevatedButton)


def test_download_input_card_fetch(mock_app_state):
    on_fetch = MagicMock()
    card = DownloadInputCard(
        on_fetch=on_fetch, on_paste=MagicMock(), app_state=mock_app_state
    )

    # Mock update to avoid Flet error
    card.update = MagicMock()

    # Empty url
    card.url_input.value = ""
    card._on_fetch_click(None)
    on_fetch.assert_not_called()
    assert card.url_input.error_text is not None

    # Valid url
    card.url_input.value = "http://video.com"
    card._on_fetch_click(None)
    on_fetch.assert_called_with("http://video.com")


def test_download_input_card_update_info(mock_app_state):
    card = DownloadInputCard(
        on_fetch=MagicMock(), on_paste=MagicMock(), app_state=mock_app_state
    )
    card.update = MagicMock()

    info = {"original_url": "http://youtube.com/watch?v=123", "title": "Test"}

    with patch("views.components.download_input_card.YouTubePanel") as mock_panel:
        card.update_video_info(info)
        assert card.time_start.disabled is False
        mock_panel.assert_called()
        assert card.current_panel is not None


def test_history_item_control_init():
    item = {
        "title": "Video",
        "url": "http://vid",
        "status": "Completed",
        "file_size": "10MB",
        "timestamp": 1234567890,
    }

    ctrl = HistoryItemControl(
        item, on_open_folder=MagicMock(), on_copy_url=MagicMock(), on_delete=MagicMock()
    )

    assert isinstance(ctrl, ft.Container)
