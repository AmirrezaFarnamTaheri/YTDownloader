"""
Localization Manager for handling multi-language support.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LocalizationManager:
    """
    Manages loading and retrieving localized strings.
    Static implementation as required by tests.
    """

    _strings: Dict[str, str] = {}
    _current_lang: str = "en"
    _locale_dir: str = "locales"

    @classmethod
    def load_language(cls, lang_code: str):
        """Load a language file."""
        cls._current_lang = lang_code
        cls._strings = {}

        # Try to load requested language
        file_path = Path(cls._locale_dir) / f"{lang_code}.json"
        if not file_path.exists():
            logger.warning("Locale file not found: %s", file_path)
            # Fallback to English if different
            if lang_code != "en":
                logger.info("Falling back to English")
                cls.load_language("en")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cls._strings = json.load(f)
            logger.debug("Loaded locale: %s", lang_code)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to load locale %s: %s", lang_code, e)

    @classmethod
    def get(cls, key: str, *args) -> str:
        """
        Get a localized string.
        Supports string formatting if args are provided.
        """
        val = cls._strings.get(key, key)
        if args:
            try:
                return val.format(*args)
            except Exception:  # pylint: disable=broad-exception-caught
                return val
        return val

    @classmethod
    def get_available_languages(cls) -> List[str]:
        """Get list of available language codes."""
        path = Path(cls._locale_dir)
        if not path.exists():
            return ["en"]

        langs = [f.stem for f in path.glob("*.json")]
        return sorted(langs) if langs else ["en"]
