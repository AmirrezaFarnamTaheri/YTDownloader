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

    @patch("builtins.open", new_callable=mock_open)
    def test_save_config(self, mock_file):
        ConfigManager.save_config({"test": 2})
        mock_file.assert_called_with(ANY, "w", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
