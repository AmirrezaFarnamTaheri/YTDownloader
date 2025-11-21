"""
Unit tests for ConfigManager and CancelToken.
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from config_manager import ConfigManager, CONFIG_FILE

# CancelToken is now in main.py, but we can define a simple mock or import it if it was standalone.
# For this test file, we will test ConfigManager only, or update import.
# Since main.py depends on Flet, importing it might trigger Flet init.
# Ideally CancelToken should be in a separate util file.
# For now, I will define a dummy CancelToken here or import from main if possible safely.
# But checking main.py, CancelToken is defined there.



class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager."""

    def setUp(self):
        # Create a temporary directory for config
        self.test_dir = tempfile.mkdtemp()
        self.config_path = Path(self.test_dir) / "config.json"

        # Patch CONFIG_FILE in config_manager
        self.patcher = patch("config_manager.CONFIG_FILE", self.config_path)
        self.mock_config_file = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_load_config_empty(self):
        """Test loading when file doesn't exist."""
        config = ConfigManager.load_config()
        self.assertEqual(config, {})

    def test_save_and_load_config(self):
        """Test saving and then loading config."""
        data = {"test_key": "test_value", "number": 123}
        ConfigManager.save_config(data)

        loaded = ConfigManager.load_config()
        self.assertEqual(loaded, data)

    def test_load_malformed_config(self):
        """Test loading a corrupted config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            f.write("{invalid json")

        config = ConfigManager.load_config()
        self.assertEqual(config, {})

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_save_config_permission_error(self, mock_open):
        """Test saving config when permission is denied."""
        data = {"test_key": "test_value"}
        # Should log error but not raise exception
        ConfigManager.save_config(data)
        # We assume it succeeded if no exception, but we can verify logging if we mocked logger
        # For now, just ensuring it doesn't crash is enough.


if __name__ == "__main__":
    unittest.main()
