"""
Utilities for UI components and platform interaction.
Includes robust validation and secure operations.
"""

# pylint: disable=too-many-return-statements

import ipaddress
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

import flet as ft

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class UIConstants:
    """Class to hold UI-related constants."""

    THUMBNAIL_SIZE = (160, 120)
    WINDOW_MIN_WIDTH = 1000
    WINDOW_MIN_HEIGHT = 750
    QUEUE_POLL_INTERVAL = 100
    PAUSE_SLEEP_INTERVAL = 0.5
    DEFAULT_PADDING = 10
    BUTTON_PADDING = 8
    ENTRY_PADDING = 5


def format_file_size(size_bytes: Optional[Union[float, str, int]]) -> str:
    """Format file size for display."""
    if size_bytes is None or size_bytes == "N/A":
        return "N/A"
    try:
        size = float(size_bytes)
        if size <= 0:
            return "0.00 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
    except (ValueError, TypeError):
        return "N/A"


def validate_url(url: str) -> bool:
    """
    Validate if URL is a valid http/https URL.
    """
    if not isinstance(url, str):
        return False

    url = url.strip()
    if len(url) < 8 or len(url) > 2048:
        return False

    # Strict regex for http/https
    # Checks for scheme, domain (at least one dot or localhost), and optional path
    # Does not allow user/pass in URL for UI safety
    regex = re.compile(
        r"^(?:http|https)://"  # http:// or https://
        # pylint: disable=line-too-long
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    if not regex.match(url):
        return False

    # Additional SSRF protection: block localhost and private IPs
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if hostname:
            if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
                return False
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback:
                    return False
            except ValueError:
                # Reject invalid numeric IPs like 999.999.999.999
                if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", hostname):
                    return False
                # Not an IP, hostname is fine
    except Exception:  # pylint: disable=broad-exception-caught
        return False

    return True


def validate_proxy(proxy: str) -> bool:
    """
    Validate proxy format.
    Expected: scheme://[user:pass@]host:port
    Restricts localhost and private IPs to prevent SSRF.
    """
    if not proxy or not isinstance(proxy, str):
        # Empty proxy is valid (no proxy)
        return True

    proxy = proxy.strip()
    if not proxy:
        return True

    # Check length
    if len(proxy) > 2048:
        return False

    try:
        parsed = urlparse(proxy)
        if not parsed.scheme or not parsed.scheme.startswith(
            ("http", "https", "socks4", "socks5")
        ):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Block localhost
        if hostname in ("localhost", "127.0.0.1", "::1"):
            return False

        # Block private IPs
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback:
                return False
        except ValueError:
            # Reject invalid numeric IPs like 999.999.999.999
            if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", hostname):
                return False
            # Not an IP address, domain name is fine (unless it resolves to private,
            # but that's handled at connection time usually,
            # though here we just check format and obvious bad actors)

        # Port validation
        if parsed.port is not None:
            if not 1 <= parsed.port <= 65535:
                return False
        # Proxy usually requires port? yt-dlp might default.
        # But strict validation is better.
        # If scheme is http/https, default ports exist.

        return True

    except Exception:  # pylint: disable=broad-exception-caught
        return False


def validate_rate_limit(rate_limit: str) -> bool:
    """Validate rate limit (e.g. 50K, 1.5M)."""
    if rate_limit is None:
        # None is valid (no limit)
        return True

    if not isinstance(rate_limit, str):
        # Non-string false unless it's explicitly None handled above
        return False

    s = rate_limit.strip()
    if not s:
        return True

    if s == "0":
        return False

    # Prevent extremely long strings
    if len(s) > 20:
        return False

    # Require a unit when using a decimal; allow integer without unit
    # e.g., 500K, 1.5M, 1000
    int_only = re.compile(r"^[1-9]\d*(?:/s)?$", re.IGNORECASE)
    with_unit = re.compile(r"^[1-9]\d*(\.\d+)?[KMGT](?:/s)?$", re.IGNORECASE)

    return bool(int_only.match(s) or with_unit.match(s))


def validate_output_template(template: str) -> bool:
    """
    Validate output template.
    Must not be absolute and must not contain parent directory references.
    """
    if not template or not isinstance(template, str):
        return False

    if ".." in template:
        return False

    try:
        path = Path(template)
        if path.is_absolute():
            return False
    except Exception:  # pylint: disable=broad-exception-caught
        return False

    return True


def validate_download_path(path_str: Optional[str]) -> bool:
    """
    Validate download path. Empty/None is allowed (defaults apply).
    Attempts to create the directory if it doesn't exist.
    """
    if not path_str:
        return True

    if not isinstance(path_str, str):
        return False

    try:
        raw_path = Path(path_str).expanduser()
        if not raw_path.is_absolute():
            raw_path = (Path.cwd() / raw_path).resolve()

        raw_path.mkdir(parents=True, exist_ok=True)
        return raw_path.exists() and raw_path.is_dir() and os.access(raw_path, os.W_OK)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Invalid download path '%s': %s", path_str, e)
        return False


def is_safe_path(filepath: str) -> bool:
    """
    Check if the filepath is within the user's home directory.
    Prevents access to sensitive system files.
    """
    try:
        path = Path(filepath).resolve()
        home = Path.home().resolve()
        return path.is_relative_to(home)
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available in the system path with timeout."""
    result = [False]

    def check():
        try:
            # check_output is better than which for some path envs
            # but shutil.which is safer/faster
            result[0] = shutil.which("ffmpeg") is not None
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("FFmpeg check error: %s", str(e))

    thread = threading.Thread(target=check, daemon=True)
    thread.start()
    thread.join(timeout=1.0)

    return result[0]


def _resolve_preferred_download_path(preferred_path: Optional[str]) -> Optional[str]:
    """Resolve a preferred download path if provided and writable."""
    if not preferred_path or not isinstance(preferred_path, str):
        return None

    try:
        raw_path = Path(preferred_path).expanduser()
        if not raw_path.is_absolute():
            raw_path = (Path.cwd() / raw_path).resolve()

        # Create if missing
        raw_path.mkdir(parents=True, exist_ok=True)

        if raw_path.exists() and raw_path.is_dir() and os.access(raw_path, os.W_OK):
            return str(raw_path)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Preferred download path invalid: %s", e)
    return None


def get_default_download_path(preferred_path: Optional[str] = None) -> str:
    """Get a safe default download path for the current platform."""
    resolved = _resolve_preferred_download_path(preferred_path)
    if resolved:
        return resolved

    try:
        # Check for Android/iOS specific
        home = Path.home()
        downloads = home / "Downloads"
        if downloads.exists() and os.access(downloads, os.W_OK):
            return str(downloads)
        if os.access(home, os.W_OK):
            return str(home)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("Failed to resolve default download path: %s", exc)
    return "."


# pylint: disable=too-many-return-statements


def open_folder(path: str, page: Optional[ft.Page] = None) -> bool:
    """
    Opens a folder in the system file manager.

    Args:
        path: The path to open.
        page: Optional Flet page (required for mobile/web fallback).
    """
    if not path or not isinstance(path, str):
        return False

    try:
        # Resolve path with security checks
        abs_path = os.path.abspath(os.path.expanduser(path))

        # Canonicalize path to prevent symlink attacks
        try:
            abs_path = os.path.realpath(abs_path)
        except (OSError, ValueError) as e:
            logger.warning("Failed to canonicalize path %s: %s", path, e)
            return False

        # Security check: Ensure it's a directory
        if not os.path.exists(abs_path):
            logger.warning("Path not found: %s", abs_path)
            return False

        if not os.path.isdir(abs_path):
            # If it's a file, get parent
            abs_path = os.path.dirname(abs_path)

        # Mobile / Web Logic
        if page and page.platform in [  # type: ignore
            ft.PagePlatform.ANDROID,
            ft.PagePlatform.IOS,
        ]:
            # Try launch_url with file scheme
            # Note: Mobile sandboxing often prevents this without specific permissions/plugins
            # but this is the best Flet effort.
            page.launch_url(f"file://{abs_path}")  # type: ignore
            return True

        if page and page.platform == ft.PagePlatform.MACOS:  # type: ignore
            # If running as macOS app bundle (not in browser)
            if sys.platform != "darwin":  # Remote browser?
                return False

        sys_plat = platform.system()

        if sys_plat == "Windows":
            # pylint: disable=no-member
            os.startfile(abs_path)  # type: ignore
            return True

        cmd = ["open", abs_path] if sys_plat == "Darwin" else ["xdg-open", abs_path]

        # pylint: disable=consider-using-with
        # Use Popen to avoid blocking
        # Redirect stdout/stderr to avoid leaking descriptors or output
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Failed to open folder: %s", str(e))
        return False


# pylint: disable=too-many-return-statements


def play_file(path: str, page: Optional[ft.Page] = None) -> bool:
    """
    Opens/Plays a file in the default system application.

    Args:
        path: The path of the file to play.
        page: Optional Flet page (required for mobile/web fallback).
    """
    if not path or not isinstance(path, str):
        return False

    try:
        abs_path = os.path.abspath(os.path.expanduser(path))

        # Canonicalize path to prevent symlink attacks
        try:
            abs_path = os.path.realpath(abs_path)
        except (OSError, ValueError) as e:
            logger.warning("Failed to canonicalize path %s: %s", path, e)
            return False

        if not os.path.exists(abs_path):
            return False

        # Ensure it's a file, not a directory
        if not os.path.isfile(abs_path):
            logger.warning("Path is not a file: %s", abs_path)
            return False

        # Mobile / Web Logic
        if page and page.platform in [  # type: ignore
            ft.PagePlatform.ANDROID,
            ft.PagePlatform.IOS,
        ]:
            page.launch_url(f"file://{abs_path}")  # type: ignore
            return True

        if page and page.platform == ft.PagePlatform.MACOS:  # type: ignore
            if sys.platform != "darwin":
                return False

        sys_plat = platform.system()

        if sys_plat == "Windows":
            # pylint: disable=no-member
            os.startfile(abs_path)  # type: ignore
            # pylint: disable=consider-using-with
            return True

        cmd = ["open", abs_path] if sys_plat == "Darwin" else ["xdg-open", abs_path]
        # pylint: disable=consider-using-with
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("Failed to play file: %s", str(e))
        return False
