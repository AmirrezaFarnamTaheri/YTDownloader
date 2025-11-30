import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from config_manager import CONFIG_FILE, ConfigManager


class TestConfigManagerCoverage(unittest.TestCase):
    @patch("config_manager.CONFIG_FILE")
    def test_load_config_backup_failure(self, mock_config_file):
        """Test failure to backup corrupted config file."""
        mock_config_file.parent = Path("/tmp")
        mock_config_file.exists.return_value = True

        # Simulate corrupted JSON
        with patch("builtins.open", new_callable=MagicMock) as mock_open:
            mock_file = MagicMock()
            mock_file.read.side_effect = json.JSONDecodeError("msg", "doc", 0)
            mock_open.return_value.__enter__.return_value = mock_file

            # Simulate OSError on rename
            mock_config_file.with_suffix.return_value = Path("backup.json")
            mock_config_file.rename.side_effect = OSError("Rename failed")

            # Should return empty dict and handle exception gracefully
            config = ConfigManager.load_config()
            self.assertEqual(config, {})

    @patch("config_manager.CONFIG_FILE")
    @patch("config_manager.tempfile.mkstemp")
    def test_save_config_temp_cleanup_failure(self, mock_mkstemp, mock_config_file):
        """Test failure to cleanup temp file after save error."""
        mock_config_file.parent = Path("/tmp")

        # Setup mkstemp to return a dummy FD and path
        mock_mkstemp.return_value = (1, "/tmp/temp_config.json")

        # Simulate error during write/dump
        with patch("os.fdopen", side_effect=Exception("Write failed")):
            # Simulate OSError on unlink (cleanup)
            with patch("pathlib.Path.unlink", side_effect=OSError("Unlink failed")):
                with self.assertRaises(Exception):
                    ConfigManager.save_config({"theme_mode": "Dark"})


if __name__ == "__main__":
    unittest.main()
