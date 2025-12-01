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
        mock_mkstemp.return_value = (1, "/tmp/temp_file")
        mock_fdopen.side_effect = Exception("Write failed")

        mock_path.parent.mkdir.return_value = None

        # Mock Path unlink for cleanup
        with patch("pathlib.Path.unlink") as mock_unlink:
            with self.assertRaises(Exception):
                ConfigManager.save_config({"theme_mode": "Dark"})
            mock_unlink.assert_called_with()

    @patch("config_manager.Path")
    @patch("config_manager.CONFIG_FILE")
    @patch("tempfile.mkstemp")
    @patch("os.fdopen")
    @patch("os.fsync")
    # pylint: disable=too-many-arguments, too-many-positional-arguments, unused-argument
    def test_save_config_windows_unlink(
        self, mock_fsync, mock_fdopen, mock_mkstemp, mock_config_file, mock_path_cls
    ):
        """Test Windows-specific atomic rename logic where target must be removed first."""
        mock_mkstemp.return_value = (1, "/tmp/temp_file")
        mock_fdopen.return_value.__enter__.return_value = MagicMock()

        mock_config_file.parent.mkdir.return_value = None
        mock_config_file.exists.return_value = True

        # Mock the Path instance returned by Path(temp_path)
        mock_temp_path_instance = mock_path_cls.return_value

        # Simulate Windows environment
        with patch("os.name", "nt"):
            ConfigManager.save_config({"theme_mode": "Dark"})
            # Should verify unlink was called
            mock_config_file.unlink.assert_called()
            # Verify rename was called on the temp path instance
            mock_temp_path_instance.rename.assert_called_with(mock_config_file)

    @patch("config_manager.CONFIG_FILE")
    def test_save_config_io_error_initial(self, mock_path):
        """Test saving configuration when initial directory creation fails."""
        # Simulate IOError during directory creation
        mock_path.parent.mkdir.side_effect = IOError("Permissions")
        with self.assertRaises(IOError):
            ConfigManager.save_config({})
