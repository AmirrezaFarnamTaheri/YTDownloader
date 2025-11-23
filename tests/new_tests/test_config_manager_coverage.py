import unittest
from unittest.mock import MagicMock, patch, mock_open
import json
import os
from pathlib import Path
from config_manager import ConfigManager, CONFIG_FILE


class TestConfigManagerCoverage(unittest.TestCase):

    @patch("config_manager.CONFIG_FILE")
    def test_load_config_corrupted_json(self, mock_path):
        # Setup for corrupted JSON
        mock_path.parent.mkdir.return_value = None
        mock_path.exists.return_value = True

        # Mock open to return invalid JSON
        with patch("builtins.open", mock_open(read_data="{invalid_json")):
            with patch("json.load", side_effect=json.JSONDecodeError("msg", "doc", 0)):
                # Mock rename for backup
                mock_path.with_suffix.return_value = MagicMock()
                mock_path.rename = MagicMock()

                result = ConfigManager.load_config()
                self.assertEqual(result, {})
                mock_path.rename.assert_called_once()

    @patch("config_manager.CONFIG_FILE")
    def test_load_config_validation_error(self, mock_path):
        mock_path.parent.mkdir.return_value = None
        mock_path.exists.return_value = True

        # Return valid JSON but invalid logical data
        with patch(
            "builtins.open", mock_open(read_data='{"use_aria2c": "not_boolean"}')
        ):
            with patch("json.load", return_value={"use_aria2c": "not_boolean"}):
                result = ConfigManager.load_config()
                self.assertEqual(result, {})

    @patch("config_manager.CONFIG_FILE")
    def test_load_config_io_error(self, mock_path):
        mock_path.parent.mkdir.return_value = None
        mock_path.exists.return_value = True

        with patch("builtins.open", side_effect=IOError("Disk fail")):
            result = ConfigManager.load_config()
            self.assertEqual(result, {})

    def test_validate_config_errors(self):
        # Not a dict
        with self.assertRaises(ValueError):
            ConfigManager._validate_config([])

        # Invalid gpu_accel
        with self.assertRaises(ValueError):
            ConfigManager._validate_config({"gpu_accel": "Invalid"})

        # Invalid theme_mode
        with self.assertRaises(ValueError):
            ConfigManager._validate_config({"theme_mode": "Blue"})

    @patch("config_manager.CONFIG_FILE")
    @patch("tempfile.mkstemp")
    @patch("os.fdopen")
    @patch("os.fsync")
    def test_save_config_exception_cleanup(
        self, mock_fsync, mock_fdopen, mock_mkstemp, mock_path
    ):
        # Setup to raise exception during write
        mock_mkstemp.return_value = (1, "/tmp/temp_file")
        mock_fdopen.side_effect = Exception("Write failed")

        mock_path.parent.mkdir.return_value = None

        # Mock Path unlink for cleanup
        with patch("pathlib.Path.unlink") as mock_unlink:
            with self.assertRaises(Exception):
                ConfigManager.save_config({"theme_mode": "Dark"})
            mock_unlink.assert_called_with()

    @patch("config_manager.CONFIG_FILE")
    @patch("tempfile.mkstemp")
    @patch("os.fdopen")
    @patch("os.fsync")
    def test_save_config_windows_unlink(
        self, mock_fsync, mock_fdopen, mock_mkstemp, mock_path
    ):
        mock_mkstemp.return_value = (1, "/tmp/temp_file")
        mock_fdopen.return_value.__enter__.return_value = MagicMock()

        mock_path.parent.mkdir.return_value = None
        mock_path.exists.return_value = True

        # Simulate Windows environment
        with patch("os.name", "nt"):
            with patch("pathlib.Path.rename") as mock_rename:
                ConfigManager.save_config({"theme_mode": "Dark"})
                # Should verify unlink was called
                mock_path.unlink.assert_called()

    @patch("config_manager.CONFIG_FILE")
    def test_save_config_io_error_initial(self, mock_path):
        # Simulate IOError during directory creation
        mock_path.parent.mkdir.side_effect = IOError("Permissions")
        with self.assertRaises(IOError):
            ConfigManager.save_config({})
