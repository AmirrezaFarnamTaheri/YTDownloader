from unittest.mock import mock_open, patch

import pytest

from sync_manager import SyncManager


def test_export_data_failure():
    """Test export_data failure handling."""
    # We need to mock tempfile creation or fdopen to fail
    with patch("tempfile.mkstemp", side_effect=IOError("Write error")):
        with pytest.raises(IOError):
            SyncManager.export_data("/tmp/test.json")


def test_import_data_failure():
    """Test import_data failure handling during read/parse."""
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", side_effect=IOError("Read error")):
            with pytest.raises(IOError):
                SyncManager.import_data("/tmp/test.json")
