import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_FILE = Path.home() / ".streamcatch" / "config.json"


class ConfigManager:
    """Manages application configuration."""

    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Load configuration from file."""
        logger.debug("Attempting to load configuration from %s", CONFIG_FILE)
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(
                        "Configuration loaded successfully: keys=%s", list(data.keys())
                    )
                    return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load config: {e}")
        return {}

    @staticmethod
    def save_config(config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        logger.debug(
            "Persisting configuration to %s with keys=%s",
            CONFIG_FILE,
            list(config.keys()),
        )
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            logger.info("Configuration saved successfully")
        except IOError as e:
            logger.error(f"Failed to save config: {e}")
