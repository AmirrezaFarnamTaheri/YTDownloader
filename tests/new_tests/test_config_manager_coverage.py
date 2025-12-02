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
    @patch("os.path.exists") # Mock os.path.exists to handle backup existence checks
    @patch("os.unlink")
    def test_load_config_corrupted_json(self, mock_unlink, mock_exists, mock_path):
        """Test loading configuration when JSON is corrupted."""
        # Setup for corrupted JSON
        mock_path.parent.mkdir.return_value = None
        # mock_path.exists.return_value = True # This is handled by os.path.exists patch if using Path.exists?
        # Wait, if CONFIG_FILE is a Path object, config_path.exists() uses Path.exists.
        # But `if os.path.exists(backup):` uses os.path.exists.

        mock_path.exists.return_value = True

        # When checking backup existence, return False to avoid unlink
        mock_exists.side_effect = lambda p: p == mock_path if isinstance(p, MagicMock) else False

        # Mock open to return invalid JSON
        with patch("builtins.open", mock_open(read_data="{invalid_json")):
            with patch("json.load", side_effect=json.JSONDecodeError("msg", "doc", 0)):
                # Mock rename for backup
                mock_path.with_suffix.return_value = MagicMock()
                mock_path.rename = MagicMock()

                result = ConfigManager.load_config()
                # Should return DEFAULTS, not empty dict
                self.assertEqual(result, ConfigManager.DEFAULTS)
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
                # Should return DEFAULTS
                self.assertEqual(result, ConfigManager.DEFAULTS)

    @patch("config_manager.CONFIG_FILE")
    def test_load_config_io_error(self, mock_path):
        """Test loading configuration when IO error occurs."""
        mock_path.parent.mkdir.return_value = None
        mock_path.exists.return_value = True

        with patch("builtins.open", side_effect=IOError("Disk fail")):
            result = ConfigManager.load_config()
            # Should return DEFAULTS
            self.assertEqual(result, ConfigManager.DEFAULTS)

    def test_validate_config_errors(self):
        """Test validation logic for various invalid inputs."""
        # Not a dict
        with self.assertRaises(ValueError):
            ConfigManager._validate_config([])

        # Invalid gpu_accel
        with self.assertRaises(ValueError):
            ConfigManager._validate_config({"gpu_accel": 123}) # Must be string

    @patch("config_manager.CONFIG_FILE")
    @patch("tempfile.mkstemp")
    @patch("os.fdopen")
    @patch("os.fsync")
    @patch("os.unlink") # Mock os.unlink for cleanup
    @patch("os.chmod") # Mock os.chmod
    def test_save_config_exception_cleanup(
        self, mock_chmod, mock_unlink, mock_fsync, mock_fdopen, mock_mkstemp, mock_path
    ):
        """Test that temporary files are cleaned up if saving fails."""
        # Setup to raise exception during write
        temp_path_str = "/tmp/temp_file"
        mock_mkstemp.return_value = (1, temp_path_str)
        mock_fdopen.side_effect = Exception("Write failed")

        mock_path.parent.mkdir.return_value = None

        # We need to ensure os.path.exists returns True for the temp file to trigger unlink
        with patch("os.path.exists", return_value=True):
             with self.assertRaises(Exception):
                ConfigManager.save_config({"theme_mode": "Dark"})

             mock_unlink.assert_called_with(temp_path_str)

    @patch("config_manager.CONFIG_FILE")
    @patch("tempfile.mkstemp")
    @patch("os.fdopen")
    @patch("os.fsync")
    @patch("os.replace") # Use os.replace instead of Path.replace
    @patch("os.chmod")
    def test_save_config_atomic_replace(
        self, mock_chmod, mock_replace, mock_fsync, mock_fdopen, mock_mkstemp, mock_config_file
    ):
        """Test atomic replace logic."""
        temp_path_str = "/tmp/temp_file"
        mock_mkstemp.return_value = (1, temp_path_str)
        mock_fdopen.return_value.__enter__.return_value = MagicMock()

        mock_config_file.parent.mkdir.return_value = None
        mock_config_file.exists.return_value = True

        # Ensure validation passes
        ConfigManager.save_config({"theme_mode": "System"})

        # Verify replace was called
        mock_replace.assert_called_with(temp_path_str, str(mock_config_file))
        mock_chmod.assert_called_with(temp_path_str, 0o600)

    @patch("config_manager.CONFIG_FILE")
    def test_save_config_io_error_initial(self, mock_path):
        """Test saving configuration when initial directory creation fails."""
        # Simulate IOError during directory creation
        mock_path.parent.mkdir.side_effect = IOError("Permissions")
        with self.assertRaises(IOError):
            ConfigManager.save_config({})
