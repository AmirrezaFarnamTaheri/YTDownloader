"""
Tests for ConfigManager class.

Covers loading, saving, validation, and error handling with high coverage.
"""

import json
import unittest
from unittest.mock import MagicMock, mock_open, patch

from config_manager import ConfigManager


class TestConfigManagerCoverage(unittest.TestCase):
    """Test suite for ConfigManager."""

    @patch("config_manager.CONFIG_FILE")
    def test_load_config_corrupted_json(self, mock_path):
        """Test loading configuration when JSON is corrupted."""
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
        """Test loading configuration that fails validation."""
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
        """Test loading configuration when IO error occurs."""
        mock_path.parent.mkdir.return_value = None
        mock_path.exists.return_value = True

        with patch("builtins.open", side_effect=IOError("Disk fail")):
            result = ConfigManager.load_config()
            self.assertEqual(result, {})

    def test_validate_config_errors(self):
        """Test validation logic for various invalid inputs."""
        # Not a dict
        with self.assertRaises(ValueError):
            # pylint: disable=protected-access
            ConfigManager._validate_config([])

        # Invalid gpu_accel
        with self.assertRaises(ValueError):
            # pylint: disable=protected-access
            ConfigManager._validate_config({"gpu_accel": "Invalid"})

        # Invalid theme_mode
        with self.assertRaises(ValueError):
            # pylint: disable=protected-access
            ConfigManager._validate_config({"theme_mode": "Blue"})

    @patch("config_manager.CONFIG_FILE")
    @patch("tempfile.mkstemp")
    @patch("os.fdopen")
    @patch("os.fsync")
    def test_save_config_exception_cleanup(
        self, mock_fsync, mock_fdopen, mock_mkstemp, mock_path
    ):
        """Test that temporary files are cleaned up if saving fails."""
        # Setup to raise exception during write
        temp_path_str = "/tmp/temp_file"
        mock_mkstemp.return_value = (1, temp_path_str)
        mock_fdopen.side_effect = Exception("Write failed")

        mock_path.parent.mkdir.return_value = None

        with patch("config_manager.Path") as mock_path_cls:
            temp_path_instance = MagicMock()
            other_instance = MagicMock()
            mock_path_cls.side_effect = lambda p: temp_path_instance if p == temp_path_str else other_instance

            with self.assertRaises(Exception):
                ConfigManager.save_config({"theme_mode": "Dark"})

            # Ensure unlink called on the temp path instance specifically
            temp_path_instance.unlink.assert_called_once_with()
            other_instance.unlink.assert_not_called()

    @patch("config_manager.Path")
    @patch("config_manager.CONFIG_FILE")
    @patch("tempfile.mkstemp")
    @patch("os.fdopen")
    @patch("os.fsync")
    # pylint: disable=too-many-arguments, too-many-positional-arguments, unused-argument
    def test_save_config_atomic_replace(
        self, mock_fsync, mock_fdopen, mock_mkstemp, mock_config_file, mock_path_cls
    ):
        """Test atomic replace logic."""
        temp_path_str = "/tmp/temp_file"
        mock_mkstemp.return_value = (1, temp_path_str)
        mock_fdopen.return_value.__enter__.return_value = MagicMock()

        mock_config_file.parent.mkdir.return_value = None
        mock_config_file.exists.return_value = True

        # Mock the Path instance returned by Path(temp_path)
        mock_temp_path_instance = MagicMock()
        mock_path_cls.side_effect = lambda p: mock_temp_path_instance if p == temp_path_str else MagicMock()

        ConfigManager.save_config({"theme_mode": "Dark"})

        # Verify replace was called on the temp path instance
        mock_temp_path_instance.replace.assert_called_with(mock_config_file)

        # Verify unlink was NOT called on config file (old windows logic)
        mock_config_file.unlink.assert_not_called()

    @patch("config_manager.CONFIG_FILE")
    def test_save_config_io_error_initial(self, mock_path):
        """Test saving configuration when initial directory creation fails."""
        # Simulate IOError during directory creation
        mock_path.parent.mkdir.side_effect = IOError("Permissions")
        with self.assertRaises(IOError):
            ConfigManager.save_config({})
