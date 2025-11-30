import json
import logging
import threading
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class LocalizationManager:
    """Manages localization strings."""

    _strings: Dict[str, str] = {}
    _current_lang: str = "en"
    _lock = threading.RLock()

    @classmethod
    def load_language(cls, lang_code: str) -> None:
        """Load a language file."""
        try:
            logger.debug(f"Loading language: {lang_code}")
            path = Path(__file__).parent / "locales" / f"{lang_code}.json"
            if path.exists():
                with cls._lock:
                    with open(path, "r", encoding="utf-8") as f:
                        cls._strings = json.load(f)
                        cls._current_lang = lang_code
                logger.info(
                    f"Loaded language '{lang_code}' with {len(cls._strings)} strings"
                )
            else:
                logger.warning(
                    f"Language file {path} not found. Falling back to English."
                )
                if lang_code != "en":
                    cls.load_language("en")

        except Exception as e:
            logger.error(f"Error loading language {lang_code}: {e}", exc_info=True)

    @classmethod
    def get(cls, key: str, *args) -> str:
        """Get a localized string."""
        with cls._lock:
            val = cls._strings.get(key, key)
        if args:
            try:
                return val.format(*args)
            except IndexError:
                logger.warning(f"Formatting error for key '{key}' with args {args}")
                return val
        return val

    @classmethod
    def get_available_languages(cls) -> list:
        """Get list of available language codes."""
        locales_dir = Path(__file__).parent / "locales"
        if locales_dir.exists():
            langs = [f.stem for f in locales_dir.glob("*.json")]
            logger.debug(f"Available languages: {langs}")
            return langs
        logger.warning("Locales directory not found.")
        return ["en"]
