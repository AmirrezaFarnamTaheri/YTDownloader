from unittest.mock import MagicMock, patch

import pytest

import app_state
from views.history_view import HistoryView


@pytest.fixture
def mock_history_view():
    with patch("views.history_view.ft") as mock_ft:
        # We need to mock BaseView or ensure it works with mocked ft
        # views.history_view imports BaseView.
        # But conftest mocks flet globally in sys.modules, so BaseView should pick up mock flet.
        return HistoryView()


def test_load_history_success():
    # Setup
    mock_hm = MagicMock()
    mock_hm.get_history.return_value = [
        {"id": "1", "url": "test", "status": "finished"}
    ]

    with patch("app_state.state.history_manager", mock_hm):
        view = HistoryView()
        view.page = MagicMock()
        view.history_list = MagicMock()
        view.history_list.controls = []

        view.load()

        # Verify
        mock_hm.get_history.assert_called_once()
        assert len(view.history_list.controls) == 1


def test_load_history_empty():
    mock_hm = MagicMock()
    mock_hm.get_history.return_value = []

    with patch("app_state.state.history_manager", mock_hm):
        view = HistoryView()
        view.page = MagicMock()
        view.history_list = MagicMock()
        view.history_list.controls = []

        view.load()

        # Should add empty state container
        assert len(view.history_list.controls) == 1
        # Check load more visibility
        assert view.load_more_btn.visible is False


def test_clear_history_flow():
    mock_hm = MagicMock()

    with patch("app_state.state.history_manager", mock_hm):
        view = HistoryView()
        view.page = MagicMock()

        # Trigger clear history
        view.clear_history(None)

        # Verify dialog opened
        view.page.open.assert_called_once()
        dialog = view.page.open.call_args[0][0]

        # Verify dialog actions
        assert len(dialog.actions) == 2

        # Simulate "Yes" click
        yes_btn = dialog.actions[0]
        yes_btn.on_click(None)

        # Verify history cleared
        mock_hm.clear_history.assert_called_once()

        # Verify snackbar shown
        assert view.page.open.call_count >= 2  # Dialog + Snackbar


def test_delete_item():
    mock_hm = MagicMock()

    with patch("app_state.state.history_manager", mock_hm):
        view = HistoryView()
        view.page = MagicMock()

        item = {"id": "123"}
        view._delete_item(item)

        mock_hm.delete_entry.assert_called_with("123")

        # Should reload
        mock_hm.get_history.assert_called()


def test_copy_url_safe():
    view = HistoryView()
    view.page = MagicMock()

    view._copy_url_safe("http://test.com")

    view.page.set_clipboard.assert_called_with("http://test.com")
    view.page.open.assert_called_once()  # Snackbar


def test_search_history():
    mock_hm = MagicMock()
    with patch("app_state.state.history_manager", mock_hm):
        view = HistoryView()
        view.search_field = MagicMock()
        view.search_field.value = " cat "

        # We need to mock load, but load is instance method.
        # Can patch it on instance.
        view.load = MagicMock()

        view._on_search_submit(None)

        assert view.current_search == "cat"
        view.load.assert_called_with(reset=True)
