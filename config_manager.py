"""
Configuration management module.

Handles loading, saving, and validating application configuration
with atomic file operations and error recovery.
"""

import json
import logging
import os
import tempfile
import uuid
import base64
from pathlib import Path
from typing import Any, Literal, cast

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
    def _validate_schema(config: dict[str, Any]) -> None:
        """
        Refactored schema validation using strict type checking.
        Validates structure and value constraints.
        """
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        # Type mapping for simple fields
        type_map = {
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
            if val not in ["system", "light", "dark"]:
                raise ValueError("theme_mode must be one of: System, Light, Dark")

        if "max_concurrent_downloads" in config:
            val = config["max_concurrent_downloads"]
            if not isinstance(val, int) or val < 1:
                raise ValueError("max_concurrent_downloads must be a positive integer")

        if "auto_sync_interval" in config:
            val = config["auto_sync_interval"]
            if not isinstance(val, (int, float)) or val <= 0:
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

    @staticmethod
    def _get_key() -> bytes:
        """Generate a stable machine-specific key."""
        node = uuid.getnode()
        # Convert to bytes
        return str(node).encode('utf-8')

    @staticmethod
    def _xor_cipher(data: str, key: bytes) -> str:
        """Simple XOR cipher."""
        data_bytes = data.encode('utf-8')
        result = bytearray()
        for i, b in enumerate(data_bytes):
            result.append(b ^ key[i % len(key)])
        return result.decode('latin1') # latin1 preserves bytes 0-255

    @staticmethod
    def _obfuscate(text: str) -> str:
        """Obfuscate string."""
        if not text:
            return ""
        try:
            key = ConfigManager._get_key()
            # First XOR
            xored = ConfigManager._xor_cipher(text, key)
            # Then base64 encode to ensure it's safe for JSON
            return base64.b64encode(xored.encode('latin1')).decode('ascii')
        except Exception as e:
            logger.warning("Obfuscation failed: %s", e)
            return ""

    @staticmethod
    def _deobfuscate(encoded_text: str) -> str:
        """Deobfuscate string."""
        if not encoded_text:
            return ""
        try:
            key = ConfigManager._get_key()
            decoded = base64.b64decode(encoded_text).decode('latin1')
            return ConfigManager._xor_cipher(decoded, key)
        except Exception: # pylint: disable=broad-exception-caught
            return ""

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

                    # Deobfuscate cookies if present
                    if "cookies" in data and isinstance(data["cookies"], str):
                        # If it looks like base64, try to deobfuscate
                        # Simple heuristic: if it contains valid cookie content (e.g. "domain"),
                        # it might be plain text from old version.
                        # If we assume all new cookies are obfuscated, we should try deobfuscate.
                        # If deobfuscation fails (e.g. not b64), fallback to raw.
                        val = data["cookies"]
                        try:
                            deobfuscated = ConfigManager._deobfuscate(val)
                            # Basic validation that result is meaningful text not garbage
                            # If result is empty but input wasn't, something failed
                            if not deobfuscated and val:
                                logger.warning("Deobfuscation returned empty, assuming plain text")
                            else:
                                data["cookies"] = deobfuscated
                        except Exception:
                            # Fallback to plain text if logic fails
                            pass

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
        """
        config_path = ConfigManager._resolve_config_file()

        # Create copy to avoid modifying the in-memory config object passed in
        save_data = config.copy()

        ConfigManager._validate_schema(save_data)

        # Obfuscate cookies
        if "cookies" in save_data and save_data["cookies"]:
            save_data["cookies"] = ConfigManager._obfuscate(save_data["cookies"])

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
