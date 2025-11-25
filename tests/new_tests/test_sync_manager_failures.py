import pytest
from unittest.mock import patch, mock_open
from sync_manager import SyncManager


def test_export_data_failure():
    """Test export_data failure handling."""
    with patch("builtins.open", side_effect=IOError("Write error")):
        with pytest.raises(IOError):
            SyncManager.export_data("/tmp/test.json")


def test_import_data_failure():
    """Test import_data failure handling during read/parse."""
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", side_effect=IOError("Read error")):
            with pytest.raises(IOError):
                SyncManager.import_data("/tmp/test.json")
