import unittest
from unittest.mock import MagicMock, patch, ANY, mock_open
import sys
import os

# Adjust path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": 1}')
    @patch("config_manager.Path.exists", return_value=True)
    def test_load_config(self, mock_exists, mock_file):
        config = ConfigManager.load_config()
        self.assertEqual(config.get("test"), 1)

    @patch("config_manager.Path.rename")
    @patch("config_manager.tempfile.mkstemp")
    @patch("os.fdopen", new_callable=mock_open)
    @patch("os.fsync")
    def test_save_config(self, mock_fsync, mock_fdopen, mock_mkstemp, mock_rename):
        # Mock tempfile creation
        mock_mkstemp.return_value = (999, "/tmp/test_config.json")

        # Test saving config with valid data
        config_data = {"use_aria2c": True, "theme_mode": "Dark"}
        ConfigManager.save_config(config_data)

        # Verify that atomic write operations were called
        mock_mkstemp.assert_called_once()
        mock_fdopen.assert_called_once()
        mock_fsync.assert_called_once()
        mock_rename.assert_called_once()


if __name__ == "__main__":
    unittest.main()
