# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Tests for ConfigManager.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):

    def setUp(self):
        # Use a temporary config file
        self.config_path = Path("test_config.json")
        # Patch the class-level CONFIG_FILE or where it's used.
        # Since CONFIG_FILE is module level global in config_manager,
        # and ConfigManager methods use it, we can patch `config_manager.CONFIG_FILE`.
        self.patcher = patch("config_manager.CONFIG_FILE", self.config_path)
        self.mock_config_file = self.patcher.start()

        # Ensure it doesn't exist
        if self.config_path.exists():
            os.remove(self.config_path)

    def tearDown(self):
        self.patcher.stop()
        if self.config_path.exists():
            try:
                os.remove(self.config_path)
            except OSError:
                pass

        # Cleanup backups
        backup = self.config_path.with_suffix(".json.bak")
        if backup.exists():
            os.remove(backup)

    def test_load_config_defaults(self):
        """Test loading defaults."""
        config = ConfigManager.load_config()
        self.assertEqual(config["theme_mode"], "System")

    def test_load_config_empty(self):
        """Test loading when file doesn't exist."""
        config = ConfigManager.load_config()
        # Should return DEFAULTS
        self.assertEqual(config, ConfigManager.DEFAULTS)

    def test_save_and_load_config(self):
        """Test saving and then loading config."""
        data = {"theme_mode": "Dark", "use_aria2c": True}
        ConfigManager.save_config(data)

        loaded = ConfigManager.load_config()
        # loaded should contain data + defaults for missing keys
        self.assertEqual(loaded["theme_mode"], "Dark")
        self.assertTrue(loaded["use_aria2c"])
        self.assertEqual(loaded["language"], "en")

    def test_load_malformed_config(self):
        """Test loading a corrupted config file."""
        # Ensure dir exists if test runs isolated
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # pylint: disable=unspecified-encoding
        with open(self.config_path, "w") as f:
            f.write("{invalid json")

        config = ConfigManager.load_config()
        # Should return DEFAULTS on error
        self.assertEqual(config, ConfigManager.DEFAULTS)
