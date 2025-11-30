import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_FILE = Path.home() / ".streamcatch" / "config.json"


class ConfigManager:
    """Manages application configuration with validation and atomic writes."""

    # Configuration schema for validation
    VALID_KEYS = {
        "proxy",
        "rate_limit",
        "output_template",
        "use_aria2c",
        "gpu_accel",
        "theme_mode",
        "language",
        # Feature-specific keys
        "rss_feeds",
    }

    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> None:
        """
        Validate configuration data.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if not isinstance(config, dict):
            logger.error(f"Invalid config type: {type(config)}")
            raise ValueError("Configuration must be a dictionary")

        # Validate known keys
        for key in config.keys():
            if key not in ConfigManager.VALID_KEYS:
                logger.warning(f"Unknown configuration key: {key}")

        # Validate specific values
        if "use_aria2c" in config and not isinstance(config["use_aria2c"], bool):
            raise ValueError("use_aria2c must be a boolean")

        if "gpu_accel" in config:
            # Normalize valid values for check if needed or just check against list
            # The UI might send lowercase, so we might want to be permissive here
            # or normalize it before saving.
            # However, for validation, let's accept strict case or allow case-insensitivity
            # if we normalize later. But save_config calls validate first.
            # Let's fix the validation to allow "auto" (lowercase) as well.
            valid_accels = ("None", "Auto", "auto", "cuda", "vulkan")
            if config["gpu_accel"] not in valid_accels:
                logger.error(f"Invalid gpu_accel value: {config['gpu_accel']}")
                raise ValueError(f"Invalid gpu_accel value: {config['gpu_accel']}")

        if "theme_mode" in config and config["theme_mode"] not in (
            "Dark",
            "Light",
            "System",
        ):
            logger.error(f"Invalid theme_mode value: {config['theme_mode']}")
            raise ValueError(f"Invalid theme_mode value: {config['theme_mode']}")

    @staticmethod
    def load_config() -> Dict[str, Any]:
        """
        Load configuration from file with error recovery.

        Returns:
            Configuration dictionary (empty if file doesn't exist or is corrupted)
        """
        logger.info(f"Loading configuration from {CONFIG_FILE}")
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    ConfigManager._validate_config(data)
                    logger.info(
                        "Configuration loaded successfully: keys=%s", list(data.keys())
                    )
                    return data
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Configuration file corrupted, using defaults: {e}", exc_info=True
                )
                # Attempt to backup corrupted file
                backup_path = CONFIG_FILE.with_suffix(".json.corrupt")
                try:
                    CONFIG_FILE.rename(backup_path)
                    logger.info(f"Corrupted config backed up to {backup_path}")
                except OSError:
                    pass
                return {}
            except ValueError as e:
                logger.warning(
                    f"Configuration validation failed, using defaults: {e}",
                    exc_info=True,
                )
                return {}
            except IOError as e:
                logger.info(f"No existing config file, will create on save: {e}")
                return {}

        logger.info("No configuration file found, using defaults")
        return {}

    @staticmethod
    def save_config(config: Dict[str, Any]) -> None:
        """
        Save configuration to file with atomic write operation.

        Args:
            config: Configuration dictionary to save

        Raises:
            ValueError: If configuration is invalid
            IOError: If save operation fails
        """
        logger.debug(
            "Persisting configuration to %s with keys=%s",
            CONFIG_FILE,
            list(config.keys()),
        )

        # Validate before saving
        ConfigManager._validate_config(config)

        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write: write to temp file, then rename
            # This prevents corruption if program crashes during write
            fd, temp_path = tempfile.mkstemp(
                dir=CONFIG_FILE.parent, prefix=".config_tmp_", suffix=".json"
            )

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk

                # Atomic rename (POSIX systems)
                # On Windows, need to remove target first
                if os.name == "nt" and CONFIG_FILE.exists():
                    logger.debug(
                        f"Removing existing config file on Windows: {CONFIG_FILE}"
                    )
                    CONFIG_FILE.unlink()

                Path(temp_path).rename(CONFIG_FILE)
                logger.info("Configuration saved successfully")

            except Exception as e:
                # Cleanup temp file on error
                try:
                    Path(temp_path).unlink()
                except OSError:
                    pass
                raise

        except IOError as e:
            logger.error(f"Failed to save config: {e}", exc_info=True)
            raise
