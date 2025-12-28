# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Unit tests for ConfigManager.
"""

import unittest
from unittest.mock import mock_open, patch

from config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):

    @patch("config_manager.os.replace")
    @patch("config_manager.tempfile.mkstemp")
    @patch("os.fdopen", new_callable=mock_open)
    @patch("os.fsync")
    @patch("os.chmod")
    def test_save_config(
        self, mock_chmod, mock_fsync, mock_fdopen, mock_mkstemp, mock_replace
    ):
        # Mock tempfile creation
        mock_mkstemp.return_value = (999, "/tmp/test_config.json")

        # Test saving config with valid data
        config_data = {"use_aria2c": True, "theme_mode": "Dark"}
        ConfigManager.save_config(config_data)

        # Check if os.replace called
        mock_replace.assert_called()

        # Check permissions - should be called at least once on temp file
        # Now also called on final file for security
        assert mock_chmod.call_count >= 1
        # Verify chmod was called with 0o600 at least once
        assert any(call[0][1] == 0o600 for call in mock_chmod.call_args_list)

    def test_save_config_validation(self):
        # Invalid type should raise ValueError
        with self.assertRaises(ValueError):
            ConfigManager.save_config([])

        # Invalid field type should raise ValueError
        with self.assertRaises(ValueError):
            ConfigManager.save_config({"use_aria2c": "True"})
