import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

class LocalizationManager:
    """Manages localization strings."""

    _strings: Dict[str, str] = {}
    _current_lang: str = "en"

    @classmethod
    def load_language(cls, lang_code: str) -> None:
        """Load a language file."""
        try:
            path = Path(__file__).parent / "locales" / f"{lang_code}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    cls._strings = json.load(f)
                    cls._current_lang = lang_code
            else:
                logger.warning(
                    f"Language file {path} not found. Falling back to English."
                )
                if lang_code != "en":
                    cls.load_language("en")

        except Exception as e:
            logger.error(f"Error loading language {lang_code}: {e}")

    @classmethod
    def get(cls, key: str, *args) -> str:
        """Get a localized string."""
        val = cls._strings.get(key, key)
        if args:
            return val.format(*args)
        return val

    @classmethod
    def get_available_languages(cls) -> list:
        """Get list of available language codes."""
        locales_dir = Path(__file__).parent / "locales"
        if locales_dir.exists():
            return [f.stem for f in locales_dir.glob("*.json")]
        return ["en"]
