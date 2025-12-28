"""
Localization Manager for handling multi-language support.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalizationManager:
    """
    Manages loading and retrieving localized strings.
    Static implementation as required by tests.
    """

    _strings: dict[str, str] = {}
    _fallback_strings: dict[str, str] = {}
    _current_lang: str = "en"
    _locale_dir: Path = Path(__file__).resolve().parent / "locales"

    @classmethod
    def _load_file(cls, file_path: Path) -> dict[str, str]:
        """Load a locale JSON file into a dict of strings."""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Locale file must contain a JSON object")
            return {str(k): str(v) for k, v in data.items()}
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to load locale file %s: %s", file_path, e)
            return {}

    @classmethod
    def load_language(cls, lang_code: str):
        """Load a language file."""
        # Security: Prevent path traversal
        if not isinstance(lang_code, str):
            logger.warning("Invalid language code type, falling back to English")
            lang_code = "en"

        if ".." in lang_code or "/" in lang_code or "\\" in lang_code:
            logger.warning("Invalid language code detected: %s", lang_code)
            lang_code = "en"

        lang_code = lang_code.strip().lower() or "en"
        cls._current_lang = lang_code
        cls._strings = {}
        cls._fallback_strings = {}

        # Try to load requested language
        file_path = cls._locale_dir / f"{lang_code}.json"
        if not file_path.exists():
            logger.warning("Locale file not found: %s", file_path)
            # Fallback to English if different
            if lang_code != "en":
                logger.info("Falling back to English")
                cls._current_lang = "en"
                file_path = cls._locale_dir / "en.json"
            else:
                return

        cls._strings = cls._load_file(file_path)
        logger.debug("Loaded locale: %s", cls._current_lang)

        # Load English fallback to avoid showing raw keys when translations are missing
        if cls._current_lang != "en":
            fallback_path = cls._locale_dir / "en.json"
            if fallback_path.exists():
                cls._fallback_strings = cls._load_file(fallback_path)

    @classmethod
    def get(cls, key: str, *args) -> str:
        """
        Get a localized string.
        Supports string formatting if args are provided.
        """
        val = cls._strings.get(key)
        if val is None and cls._fallback_strings:
            val = cls._fallback_strings.get(key)
        if val is None:
            val = key

        # Log warning for missing keys in development
        if val == key and key not in ("", None):
            logger.debug(
                "Missing localization key: %s (lang=%s)", key, cls._current_lang
            )

        if args:
            try:
                return val.format(*args)
            except Exception:  # pylint: disable=broad-exception-caught
                return val
        return val

    @classmethod
    def get_available_languages(cls) -> list[str]:
        """Get list of available language codes."""
        path = cls._locale_dir
        if not path.exists():
            return ["en"]

        langs = [f.stem for f in path.glob("*.json") if f.is_file()]
        return sorted(langs) if langs else ["en"]
