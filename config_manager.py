"""
Configuration management module.

Handles loading, saving, and validating application configuration
with atomic file operations and error recovery.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Configuration file path with fallback
try:
    CONFIG_FILE = Path.home() / ".streamcatch" / "config.json"
except Exception:  # pylint: disable=broad-exception-caught
    CONFIG_FILE = Path("config.json")


class ConfigManager:
    """Manages application configuration with validation and atomic writes."""

    # Defaults and validation schema
    DEFAULTS = {
        "theme_mode": "System",
        "language": "en",
        "output_template": "%(title)s.%(ext)s",
        "use_aria2c": False,
        "gpu_accel": "None",
        "rss_feeds": [],
    }

    @staticmethod
    def _resolve_config_file() -> Path:
        """Resolve and return the correct config file path."""
        try:
            config_file = CONFIG_FILE
            if not config_file.parent.exists():
                config_file.parent.mkdir(parents=True, exist_ok=True)
            return config_file
        except OSError:
            # Fallback to local
            return Path("config.json")

    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> None:
        """
        Validate configuration data.
        """
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        # Type checking for known keys
        if "use_aria2c" in config and not isinstance(config["use_aria2c"], bool):
            raise ValueError("use_aria2c must be a boolean")

        if "rss_feeds" in config and not isinstance(config["rss_feeds"], list):
            raise ValueError("rss_feeds must be a list")

        if "gpu_accel" in config:
            val = config["gpu_accel"]
            if not isinstance(val, str):
                raise ValueError("gpu_accel must be a string")
            if val not in ["None", "auto", "cuda", "vulkan"]:
                raise ValueError(
                    f"gpu_accel must be one of: None, auto, cuda, vulkan. Got: {val}"
                )

        # Validate metadata_cache_size if present
        if "metadata_cache_size" in config:
            val = config["metadata_cache_size"]
            if not isinstance(val, int) or val < 1:
                raise ValueError("metadata_cache_size must be a positive integer")

    @staticmethod
    def load_config() -> Dict[str, Any]:
        """
        Load configuration from file with error recovery.
        """
        config_path = ConfigManager._resolve_config_file()
        logger.info("Loading config from %s", config_path)

        config = ConfigManager.DEFAULTS.copy()

        if config_path.exists():
            try:
                # Check for empty file first
                if config_path.stat().st_size == 0:
                    logger.warning("Config file is empty, using defaults")
                    return config

                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    ConfigManager._validate_config(data)
                    config.update(data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Config corrupted/invalid (%s), using defaults", e)
                # Backup corrupted file
                try:
                    backup = config_path.with_suffix(".json.bak")
                    # Use os.replace for better atomic behavior on some systems
                    # although for backup renaming is fine
                    if os.path.exists(backup):
                        os.unlink(backup)
                    config_path.rename(backup)
                except OSError:
                    pass
                return config
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Failed to load config: %s", e)
                return config

        return config

    @staticmethod
    def save_config(config: Dict[str, Any]) -> None:
        """
        Save configuration to file with atomic write operation.
        """
        config_path = ConfigManager._resolve_config_file()
        ConfigManager._validate_config(config)

        temp_path = None

        try:
            # Ensure parent dir exists
            if not config_path.parent.exists():
                config_path.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write via temp file
            fd, temp_path = tempfile.mkstemp(
                dir=str(config_path.parent),
                prefix=".config_tmp_",
                suffix=".json",
                text=True,
            )
            # Security: Set restrictive permissions
            os.chmod(temp_path, 0o600)

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic replace
                os.replace(temp_path, str(config_path))
                # Ensure secure permissions on final file
                try:
                    os.chmod(str(config_path), 0o600)
                except OSError:
                    logger.warning("Could not set secure permissions on config file")
                logger.info("Configuration saved.")

            # pylint: disable=try-except-raise
            except Exception:
                # Re-raise to be handled by outer block or just bubble up
                raise

        except Exception as e:
            logger.error("Failed to save config: %s", e)
            raise

        finally:
            # Cleanup if failed and temp file still exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
