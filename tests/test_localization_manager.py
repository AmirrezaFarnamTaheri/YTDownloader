# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
import json
import unittest
from unittest.mock import mock_open, patch

from localization_manager import LocalizationManager


class TestLocalizationManager(unittest.TestCase):

    def test_get_default(self):
        # Reset
        LocalizationManager._strings = {}
        self.assertEqual(LocalizationManager.get("test_key"), "test_key")

    def test_get_formatted(self):
        LocalizationManager._strings = {"greet": "Hello {}"}
        self.assertEqual(LocalizationManager.get("greet", "World"), "Hello World")

    @patch(
        "builtins.open", new_callable=mock_open, read_data='{"app_title": "Test App"}'
    )
    @patch("pathlib.Path.exists")
    def test_load_language_success(self, mock_exists, mock_file):
        mock_exists.return_value = True
        LocalizationManager.load_language("en")
        self.assertEqual(LocalizationManager.get("app_title"), "Test App")
        self.assertEqual(LocalizationManager._current_lang, "en")

    @patch("pathlib.Path.exists")
    def test_load_language_not_found_fallback(self, mock_exists):
        # Mock exists to return False for 'fr', but True for 'en' (second call)
        mock_exists.side_effect = [False, True]

        with patch(
            "builtins.open",
            new_callable=mock_open,
            read_data='{"app_title": "English App"}',
        ):
            LocalizationManager.load_language("fr")

        self.assertEqual(LocalizationManager.get("app_title"), "English App")

    def test_get_available_languages(self):
        with patch("pathlib.Path.glob") as mock_glob:
            mock_path1 = unittest.mock.Mock()
            mock_path1.stem = "en"
            mock_path2 = unittest.mock.Mock()
            mock_path2.stem = "es"
            mock_glob.return_value = [mock_path1, mock_path2]

            langs = LocalizationManager.get_available_languages()
            self.assertIn("en", langs)
            self.assertIn("es", langs)
