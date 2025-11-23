
import json
import pytest
from unittest.mock import patch, mock_open
from localization_manager import LocalizationManager
from pathlib import Path

def test_load_language_fallback():
    """Test falling back to English if file not found."""
    with patch("pathlib.Path.exists") as mock_exists:
        # First call (requested lang) returns False, second (en) returns True
        mock_exists.side_effect = [False, True]

        with patch("builtins.open", mock_open(read_data='{"hello": "Hello"}')):
            LocalizationManager.load_language("fr")

            # Should have tried to load English
            assert LocalizationManager._current_lang == "en"

def test_load_language_exception():
    """Test error handling during load."""
    with patch("pathlib.Path.exists", return_value=True):
        with patch("builtins.open", side_effect=IOError("Read error")):
            with patch("logging.Logger.error") as mock_log:
                LocalizationManager.load_language("en")
                mock_log.assert_called()

def test_get_available_languages_no_dir():
    """Test get_available_languages when dir missing."""
    with patch("pathlib.Path.exists", return_value=False):
        langs = LocalizationManager.get_available_languages()
        assert langs == ["en"]
