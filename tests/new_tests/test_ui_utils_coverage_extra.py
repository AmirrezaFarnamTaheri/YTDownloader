import os
from unittest.mock import MagicMock, patch

import pytest

from ui_utils import open_folder, validate_rate_limit


def test_open_folder_exceptions():
    """Test exception handling in open_folder."""
    # Test path expansion failure or generic os error
    with patch("os.path.expanduser", side_effect=Exception("Path error")):
        assert open_folder("~/Documents") is False


def test_open_folder_empty():
    """Test empty path."""
    assert open_folder("") is False
    assert open_folder(None) is False


def test_open_folder_not_exist():
    """Test non-existent path."""
    with patch("os.path.exists", return_value=False):
        assert open_folder("/non/existent") is False


def test_open_folder_platforms():
    """Test platform specific calls."""
    with patch("os.path.exists", return_value=True), patch("os.path.isdir", return_value=True):
        # Windows
        with patch("platform.system", return_value="Windows"):
            with patch("os.startfile", create=True) as mock_start:
                open_folder("C:\\")
                mock_start.assert_called()

        # Darwin
        with patch("platform.system", return_value="Darwin"):
            with patch("subprocess.Popen") as mock_popen:
                open_folder("/tmp")
                # Popen args check: stdout/stderr devnull
                args, kwargs = mock_popen.call_args
                assert args[0] == ["open", "/tmp"]

        # Linux
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.Popen") as mock_popen:
                open_folder("/tmp")
                args, kwargs = mock_popen.call_args
                assert args[0] == ["xdg-open", "/tmp"]


def test_validate_rate_limit_zero():
    """Test rate limit 0."""
    assert validate_rate_limit("0K") is False
    assert validate_rate_limit("0") is False
    assert validate_rate_limit("0.0M") is False
