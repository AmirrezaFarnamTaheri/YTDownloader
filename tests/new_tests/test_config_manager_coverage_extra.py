"""
Extra coverage tests for ConfigManager.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from config_manager import ConfigManager


class TestConfigManagerCoverage(unittest.TestCase):

    @patch("config_manager.CONFIG_FILE")
    def test_load_config_backup_failure(self, mock_config_file):
        """Test failure to backup corrupted config file."""
        mock_config_file.parent = Path("/tmp")
        mock_config_file.exists.return_value = True

        # Simulate corrupted JSON
        # Note: json.load calls f.read(), so we need to mock read?
        # No, json.load takes a file-like object.

        with patch("builtins.open", new_callable=MagicMock) as mock_open:
            # When open() is called, it returns a context manager
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            # json.load calls read() on the file object
            # BUT we are patching json.load in some tests.
            # Here we let json.load run but mock the file content?
            # Or mock json.load to raise JSONDecodeError.

            with patch("json.load", side_effect=json.JSONDecodeError("msg", "doc", 0)):
                # Simulate OSError on rename
                mock_config_file.with_suffix.return_value = Path("backup.json")
                mock_config_file.rename.side_effect = OSError("Rename failed")

                # Should return DEFAULTS and handle exception gracefully
                config = ConfigManager.load_config()
                self.assertEqual(config, ConfigManager.DEFAULTS)

    def test_validate_config_types(self):
        """Test strict type checking."""
        # ConfigManager._validate_config raises ValueError if types are wrong
        with self.assertRaises(ValueError):
            ConfigManager._validate_config({"use_aria2c": "True"}) # Should be bool

        with self.assertRaises(ValueError):
            ConfigManager._validate_config({"rss_feeds": "invalid"}) # Should be list
