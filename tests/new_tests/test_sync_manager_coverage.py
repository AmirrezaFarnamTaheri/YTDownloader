import unittest
from unittest.mock import MagicMock, patch, mock_open
import json
from sync_manager import SyncManager
from pathlib import Path


class TestSyncManagerCoverage(unittest.TestCase):

    @patch("sync_manager.ConfigManager.load_config")
    @patch("sync_manager.HistoryManager.get_history")
    def test_export_data_default_path(self, mock_get_history, mock_load_config):
        mock_load_config.return_value = {"key": "val"}
        mock_get_history.return_value = [{"url": "http"}]

        expected_path = str(Path.home() / SyncManager.EXPORT_FILE)

        # Mock tempfile and os.replace
        with patch("builtins.open", mock_open()) as mock_file:
             with patch("tempfile.mkstemp", return_value=(123, "/tmp/tempfile")):
                 with patch("os.fdopen", mock_file):
                      with patch("os.replace") as mock_replace:
                           with patch("os.fsync"): # mock fsync
                               path = SyncManager.export_data()
                               self.assertEqual(path, expected_path)
                               # It writes to temp file handle
                               mock_file.assert_called()
                               mock_replace.assert_called_with("/tmp/tempfile", expected_path)

        # Verify json dump content
        # handle = mock_file()
            # We can't easily check the written content with json.dump directly on mock without more complex setup
            # but we know it didn't crash.

    @patch("sync_manager.ConfigManager.load_config")
    def test_export_data_failure(self, mock_load):
        mock_load.side_effect = Exception("Config error")
        with self.assertRaises(Exception):
            SyncManager.export_data()

    @patch("os.path.exists")
    def test_import_data_not_found(self, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(FileNotFoundError):
            SyncManager.import_data("dummy.json")

    @patch("os.path.exists")
    @patch("sync_manager.ConfigManager.save_config")
    @patch("sync_manager.HistoryManager.add_entry")
    def test_import_data_success(self, mock_add_entry, mock_save_config, mock_exists):
        mock_exists.return_value = True

        json_data = json.dumps(
            {
                "config": {"theme": "Dark"},
                "history": [
                    {
                        "url": "http://test",
                        "title": "Test",
                        "output_path": "/tmp",
                        "format_str": "mp4",
                    }
                ],
            }
        )

        with patch("builtins.open", mock_open(read_data=json_data)):
            SyncManager.import_data("dummy.json")

        mock_save_config.assert_called_with({"theme": "Dark"})
        mock_add_entry.assert_called_once()

    @patch("os.path.exists")
    def test_import_data_failure(self, mock_exists):
        mock_exists.return_value = True
        with patch("builtins.open", mock_open(read_data="invalid json")):
            with self.assertRaises(json.JSONDecodeError):
                SyncManager.import_data("dummy.json")
