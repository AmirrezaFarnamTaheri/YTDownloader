"""
Configuration management module.

Handles loading, saving, and validating application configuration
with atomic file operations and error recovery.
Now uses keyring for secure cookie storage.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, cast

# Import keyring when available; allow runtime without it.
try:
    import keyring
    from keyring.errors import PasswordDeleteError

    KEYRING_AVAILABLE = True
except Exception:  # pylint: disable=broad-exception-caught
    keyring = None  # type: ignore[assignment]
    PasswordDeleteError = Exception  # type: ignore[assignment,misc]
    KEYRING_AVAILABLE = False

logger = logging.getLogger(__name__)

SERVICE_NAME = "streamcatch_app"

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
    def _validate_schema(config: dict[str, Any]) -> None:
        """
        Refactored schema validation using strict type checking.
        Validates structure and value constraints.
        """
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        # Type mapping for simple fields
        type_map: dict[str, type | tuple[type, ...]] = {
            "use_aria2c": bool,
            "rss_feeds": list,
            "language": str,
            "proxy": (str, type(None)),  # Allow None but will convert/check
            "rate_limit": (str, type(None)),
            "download_path": (str, type(None)),
            "auto_sync_enabled": bool,
            "high_contrast": bool,
            "compact_mode": bool,
            "clipboard_monitor_enabled": bool,
            "output_template": str,
            "theme_mode": str,
        }

        for key, expected_type in type_map.items():
            if key in config:
                val = config[key]
                if val is not None and not isinstance(val, expected_type):
                    # Handle optional strings passed as None
                    if expected_type == (str, type(None)) and val is None:
                        continue
                    raise ValueError(f"{key} must be of type {expected_type}")

        # Specific constraints
        if "gpu_accel" in config:
            val = config["gpu_accel"]
            if not isinstance(val, str):
                raise ValueError("gpu_accel must be a string")
            if val not in ["None", "auto", "cuda", "vulkan"]:
                raise ValueError(
                    f"gpu_accel must be one of: None, auto, cuda, vulkan. Got: {val}"
                )

        if "metadata_cache_size" in config:
            val = config["metadata_cache_size"]
            if not isinstance(val, int) or val < 1:
                raise ValueError("metadata_cache_size must be a positive integer")

        if "theme_mode" in config:
            val = cast(str, config["theme_mode"]).lower()
            if val not in [
                "system",
                "light",
                "dark",
                "high contrast",
                "high_contrast",
                "high-contrast",
            ]:
                raise ValueError(
                    "theme_mode must be one of: System, Light, Dark, High Contrast"
                )

        if "max_concurrent_downloads" in config:
            val = config["max_concurrent_downloads"]
            if not isinstance(val, int) or val < 1:
                raise ValueError("max_concurrent_downloads must be a positive integer")

        if "auto_sync_interval" in config:
            val = config["auto_sync_interval"]
            if not isinstance(val, int | float) or val <= 0:
                raise ValueError("auto_sync_interval must be a positive number")

        if "output_template" in config:
            val = config["output_template"]
            if ".." in val.split(os.path.sep) or ".." in val.split("/"):
                raise ValueError("output_template must not contain '..'")
            try:
                if Path(val).is_absolute():
                    raise ValueError("output_template must be a relative path")
            except Exception as e:  # pylint: disable=broad-exception-caught
                raise ValueError(f"Invalid output_template: {e}") from e

    @staticmethod
    def _validate_config(config: dict[str, Any]) -> None:
        """Wrapper for _validate_schema for backward compatibility."""
        ConfigManager._validate_schema(config)

    # Removed XOR obfuscation methods as we use keyring now

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

                    # LOAD COOKIES FROM KEYRING
                    if KEYRING_AVAILABLE:
                        try:
                            cookies = keyring.get_password(SERVICE_NAME, "cookies")
                            if cookies:
                                # If keyring has cookies, prefer them over file
                                data["cookies"] = cookies
                            elif "cookies" in data:
                                # Fallback: Migration scenario.
                                # If file has cookies but keyring doesn't, we might want to migrate later.
                                # But for now, just use them.
                                # If they were obfuscated with old logic, they might be garbage if we removed deobfuscate logic.
                                # Since we removed _deobfuscate, we assume new version doesn't support old obfuscation.
                                # This forces a reset of cookies if they were obfuscated, which is acceptable for security upgrade.
                                # Or we can treat them as plain text if they look like it.
                                pass
                        except Exception as e:  # pylint: disable=broad-exception-caught
                            logger.warning("Failed to load cookies from keyring: %s", e)

                    ConfigManager._validate_schema(data)
                    config.update(data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Config corrupted/invalid (%s), using defaults", e)
                # Backup corrupted file
                try:
                    backup = config_path.with_suffix(".json.bak")
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
        Sensitive data (cookies) is stored in the system keyring.
        """
        config_path = ConfigManager._resolve_config_file()

        # Create copy to avoid modifying the in-memory config object passed in
        save_data = config.copy()

        ConfigManager._validate_schema(save_data)

        # SAVE COOKIES TO KEYRING
        # Unconditionally pop cookies from save_data so they are never written to disk in plain text
        cookies_val = save_data.pop("cookies", None)

        if KEYRING_AVAILABLE:
            if cookies_val:
                try:
                    keyring.set_password(SERVICE_NAME, "cookies", cookies_val)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error("Failed to save cookies to keyring: %s", e)
            else:
                # If cookies are cleared/empty, remove from keyring
                try:
                    keyring.delete_password(SERVICE_NAME, "cookies")
                except PasswordDeleteError:
                    pass  # Password didn't exist
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning("Failed to delete cookies from keyring: %s", e)
        elif cookies_val:
            logger.warning(
                "Keyring is not available; cookies are not persisted securely."
            )

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
                    json.dump(save_data, f, indent=2)
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
