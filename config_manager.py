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
from typing import Any

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
        "proxy": "",
        "rate_limit": "",
        "max_concurrent_downloads": 3,
        "download_path": "",
        "auto_sync_enabled": False,
        "auto_sync_interval": 3600.0,
        "high_contrast": False,
        "compact_mode": False,
        "metadata_cache_size": 50,
        "clipboard_monitor_enabled": False,
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
    def _validate_config(config: dict[str, Any]) -> None:
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

        if "theme_mode" in config:
            val = config["theme_mode"]
            if not isinstance(val, str):
                raise ValueError("theme_mode must be a string")
            if val.lower() not in ["system", "light", "dark"]:
                raise ValueError("theme_mode must be one of: System, Light, Dark")

        if "language" in config and not isinstance(config["language"], str):
            raise ValueError("language must be a string")

        if "proxy" in config and config["proxy"] is not None:
            if not isinstance(config["proxy"], str):
                raise ValueError("proxy must be a string")

        if "rate_limit" in config and config["rate_limit"] is not None:
            if not isinstance(config["rate_limit"], str):
                raise ValueError("rate_limit must be a string")

        if "output_template" in config:
            val = config["output_template"]
            if not isinstance(val, str):
                raise ValueError("output_template must be a string")
            # Basic path traversal guard
            if ".." in val.split(os.path.sep) or ".." in val.split("/"):
                raise ValueError("output_template must not contain '..'")
            try:
                if Path(val).is_absolute():
                    raise ValueError("output_template must be a relative path")
            except Exception as e:  # pylint: disable=broad-exception-caught
                raise ValueError(f"Invalid output_template: {e}") from e

        if "max_concurrent_downloads" in config:
            val = config["max_concurrent_downloads"]
            if not isinstance(val, int) or val < 1:
                raise ValueError("max_concurrent_downloads must be a positive integer")

        if "download_path" in config and config["download_path"] is not None:
            if not isinstance(config["download_path"], str):
                raise ValueError("download_path must be a string")

        if "auto_sync_enabled" in config and not isinstance(
            config["auto_sync_enabled"], bool
        ):
            raise ValueError("auto_sync_enabled must be a boolean")

        if "auto_sync_interval" in config:
            val = config["auto_sync_interval"]
            if not isinstance(val, (int, float)) or val <= 0:
                raise ValueError("auto_sync_interval must be a positive number")

        if "high_contrast" in config and not isinstance(config["high_contrast"], bool):
            raise ValueError("high_contrast must be a boolean")

        if "compact_mode" in config and not isinstance(config["compact_mode"], bool):
            raise ValueError("compact_mode must be a boolean")

        if "clipboard_monitor_enabled" in config and not isinstance(
            config["clipboard_monitor_enabled"], bool
        ):
            raise ValueError("clipboard_monitor_enabled must be a boolean")

    @staticmethod
    def load_config() -> dict[str, Any]:
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

                with open(config_path, encoding="utf-8") as f:
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
                except OSError as exc:
                    logger.warning("Failed to backup corrupted config: %s", exc)
                return config
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Failed to load config: %s", e)
                return config

        return config

    @staticmethod
    def save_config(config: dict[str, Any]) -> None:
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
                except OSError as exc:
                    logger.warning(
                        "Failed to remove temp config file %s: %s", temp_path, exc
                    )
