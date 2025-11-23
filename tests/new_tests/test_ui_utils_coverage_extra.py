
import pytest
from unittest.mock import patch, MagicMock
from ui_utils import open_folder, validate_rate_limit
import os

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
    with patch("os.path.exists", return_value=True):
        # Windows
        # os.startfile only exists on Windows, so we need create=True for patch if not on windows
        with patch("platform.system", return_value="Windows"):
            with patch("os.startfile", create=True) as mock_start:
                open_folder("C:\\")
                mock_start.assert_called()

        # Darwin
        with patch("platform.system", return_value="Darwin"):
            with patch("subprocess.Popen") as mock_popen:
                open_folder("/tmp")
                mock_popen.assert_called_with(["open", "/tmp"])

        # Linux
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.Popen") as mock_popen:
                open_folder("/tmp")
                mock_popen.assert_called_with(["xdg-open", "/tmp"])

def test_validate_rate_limit_zero():
    """Test rate limit 0."""
    assert validate_rate_limit("0K") is False
    assert validate_rate_limit("0") is False
    assert validate_rate_limit("0.0M") is False
