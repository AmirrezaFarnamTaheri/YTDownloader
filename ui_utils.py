"""
Utilities for UI components and platform interaction.
Includes robust validation and secure operations.
"""

import logging
import os
import platform
import re
import shutil
import subprocess
import threading
from typing import Optional, Union

logger = logging.getLogger(__name__)


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
        r'^(?:http|https)://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return bool(regex.match(url))


def validate_proxy(proxy: str) -> bool:
    """
    Validate proxy format.
    Expected: scheme://[user:pass@]host:port
    """
    if not proxy or not isinstance(proxy, str):
        return True
    proxy = proxy.strip()
    if not proxy:
        return True

    if not proxy.startswith(("http://", "https://", "socks4://", "socks5://")):
        return False

    try:
        _, rest = proxy.split("://", 1)
        if not rest: return False

        # Check for port existence (simplified)
        if ":" not in rest:
            return False

        return True
    except ValueError:
        return False


def validate_rate_limit(rate_limit: str) -> bool:
    """Validate rate limit (e.g. 50K, 1.5M)."""
    if not rate_limit or not isinstance(rate_limit, str):
        return True
    rate_limit = rate_limit.strip()
    if not rate_limit:
        return True

    return bool(re.match(r"^\d+(\.\d+)?[KMGT]?(?:/s)?$", rate_limit, re.IGNORECASE))


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available in the system path with timeout."""
    result = [False]

    def check():
        try:
            # check_output is better than which for some path envs
            # but shutil.which is safer/faster
            result[0] = shutil.which("ffmpeg") is not None
        except Exception as e:
            logger.warning("FFmpeg check error: %s", e)

    thread = threading.Thread(target=check, daemon=True)
    thread.start()
    thread.join(timeout=1.0)

    return result[0]


def open_folder(path: str) -> bool:
    """Opens a folder in the system file manager."""
    if not path:
        return False

    try:
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            logger.warning("Path not found: %s", path)
            return False

        logger.info("Opening folder: %s", path)
        if platform.system() == "Windows":
            os.startfile(path) # type: ignore
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        logger.error("Failed to open folder: %s", e)
        return False
