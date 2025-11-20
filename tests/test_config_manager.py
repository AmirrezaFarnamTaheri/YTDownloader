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
from main import CancelToken
import yt_dlp

class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager."""

    def setUp(self):
        # Create a temporary directory for config
        self.test_dir = tempfile.mkdtemp()
        self.config_path = Path(self.test_dir) / 'config.json'

        # Patch CONFIG_FILE in config_manager
        self.patcher = patch('config_manager.CONFIG_FILE', self.config_path)
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
        data = {'test_key': 'test_value', 'number': 123}
        ConfigManager.save_config(data)

        loaded = ConfigManager.load_config()
        self.assertEqual(loaded, data)

    def test_load_malformed_config(self):
        """Test loading a corrupted config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            f.write("{invalid json")

        config = ConfigManager.load_config()
        self.assertEqual(config, {})

class TestCancelToken(unittest.TestCase):
    """Test cases for CancelToken."""

    def test_initialization(self):
        token = CancelToken()
        self.assertFalse(token.cancelled)
        self.assertFalse(token.is_paused)

    def test_cancel(self):
        token = CancelToken()
        token.cancel()
        self.assertTrue(token.cancelled)

    def test_check_raises_when_cancelled(self):
        token = CancelToken()
        token.cancel()
        with self.assertRaises(yt_dlp.utils.DownloadError):
            token.check({})

    def test_pause_resume(self):
        token = CancelToken()
        token.pause()
        self.assertTrue(token.is_paused)
        token.resume()
        self.assertFalse(token.is_paused)

if __name__ == '__main__':
    unittest.main()
