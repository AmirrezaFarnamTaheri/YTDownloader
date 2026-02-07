import threading
import time
from unittest.mock import MagicMock, patch

import pytest

import clipboard_monitor
from clipboard_monitor import _clipboard_loop, start_clipboard_monitor


@pytest.fixture(autouse=True)
def reset_globals():
    clipboard_monitor._monitor_thread = None
    yield
    clipboard_monitor._monitor_thread = None


@pytest.fixture
def mock_state():
    with patch("clipboard_monitor.state") as mock:
        mock.clipboard_monitor_active = True
        mock.shutdown_flag.is_set.return_value = False
        mock.last_clipboard_content = ""
        yield mock


@pytest.fixture
def mock_pyperclip():
    with patch("clipboard_monitor.pyperclip") as mock:
        # Define the Exception class on the mock
        class MockPyperclipException(Exception):
            pass

        mock.PyperclipException = MockPyperclipException
        yield mock


def test_start_clipboard_monitor_success(mock_state, mock_pyperclip):
    page = MagicMock()
    view = MagicMock()

    with patch("threading.Thread") as mock_thread_cls:
        res = start_clipboard_monitor(page, view)
        assert res is True
        mock_thread_cls.assert_called_once()


def test_start_clipboard_monitor_failure(mock_state, mock_pyperclip):
    # Raise the mocked exception
    mock_pyperclip.paste.side_effect = mock_pyperclip.PyperclipException("No access")

    res = start_clipboard_monitor(MagicMock(), MagicMock())
    assert res is False


def test_clipboard_loop_logic(mock_state, mock_pyperclip):
    page = MagicMock()
    view = MagicMock()
    view.url_input.value = ""

    loop_count = 0

    def side_effect_sleep(sec):
        nonlocal loop_count
        loop_count += 1
        if loop_count >= 1:
            mock_state.shutdown_flag.is_set.return_value = True

    with patch("time.sleep", side_effect=side_effect_sleep):
        mock_pyperclip.paste.return_value = "http://video.com"

        _clipboard_loop(page, view)

        assert page.run_task.called
        callback = page.run_task.call_args[0][0]
        callback()

        assert view.url_input.value == "http://video.com"
