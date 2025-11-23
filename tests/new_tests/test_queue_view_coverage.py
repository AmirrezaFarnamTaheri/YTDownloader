
import flet as ft
import pytest
from unittest.mock import MagicMock, patch
from views.queue_view import QueueView

def test_queue_view_clear_finished():
    """Test clearing finished items."""
    mock_qm = MagicMock()
    mock_remove = MagicMock()

    view = QueueView(mock_qm, MagicMock(), mock_remove, MagicMock())
    view.update = MagicMock()
    view.queue_list = MagicMock()

    # Mock items - need url/title to pass DownloadItemControl init
    item1 = {"status": "Completed", "url": "http://a", "title": "A"}
    item2 = {"status": "Downloading", "url": "http://b", "title": "B"}
    item3 = {"status": "Error", "url": "http://c", "title": "C"}

    mock_qm.get_all.return_value = [item1, item2, item3]

    # Mock DownloadItemControl to prevent actual UI logic that needs Page
    with patch("views.queue_view.DownloadItemControl") as MockControl:
        mock_instance = MockControl.return_value
        # Mock view property to be a generic control
        mock_instance.view = ft.Container()

        view.clear_finished(None)

        assert mock_remove.call_count == 2
        mock_remove.assert_any_call(item1)
        mock_remove.assert_any_call(item3)
