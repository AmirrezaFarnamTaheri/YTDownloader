"""Tests for configuration helpers and cancellation token."""
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, mock_open

import yt_dlp

import main
from main import load_config, save_config, CancelToken


class TestConfigHelpers(unittest.TestCase):
    """Validate load_config and save_config behaviours."""

    def test_load_config_missing_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            with patch("main.CONFIG_FILE", config_path):
                self.assertEqual(load_config(), {})

    def test_load_config_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text("{invalid", encoding="utf-8")
            with patch("main.CONFIG_FILE", config_path):
                self.assertEqual(load_config(), {})

    def test_save_config_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            with patch("main.CONFIG_FILE", config_path):
                data = {"dark_mode": True, "quality": "1080p"}
                save_config(data)
                loaded = json.loads(config_path.read_text(encoding="utf-8"))
                self.assertEqual(loaded, data)

    def test_save_config_io_error_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            m = mock_open()
            m.side_effect = IOError("boom")
            with patch("main.CONFIG_FILE", config_path), patch("main.open", m):
                save_config({"foo": "bar"})
            self.assertFalse(config_path.exists())


class TestCancelToken(unittest.TestCase):
    """Ensure CancelToken state transitions operate as expected."""

    def test_cancel_sets_flag(self):
        token = CancelToken()
        self.assertFalse(token.cancelled)
        token.cancel()
        self.assertTrue(token.cancelled)

    def test_check_raises_when_cancelled(self):
        token = CancelToken()
        token.cancelled = True
        with self.assertRaises(yt_dlp.utils.DownloadError):
            token.check({})

    def test_check_respects_pause_and_resume(self):
        token = CancelToken()
        token.is_paused = True

        def unpause(_sleep):
            token.is_paused = False

        with patch("main.time.sleep", side_effect=unpause) as mock_sleep:
            token.check({"status": "downloading"})

        mock_sleep.assert_called()


if __name__ == "__main__":
    unittest.main()
