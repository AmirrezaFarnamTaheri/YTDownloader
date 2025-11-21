from typing import Optional
import logging
import os
import platform
import subprocess

logger = logging.getLogger(__name__)


class UIConstants:
    """Class to hold UI-related constants."""

    THUMBNAIL_SIZE = (160, 120)  # Larger thumbnail for better visibility
    WINDOW_MIN_WIDTH = 1000
    WINDOW_MIN_HEIGHT = 750
    QUEUE_POLL_INTERVAL = 100  # milliseconds
    PAUSE_SLEEP_INTERVAL = 0.5  # seconds
    DEFAULT_PADDING = 10
    BUTTON_PADDING = 8
    ENTRY_PADDING = 5


def format_file_size(size_bytes: Optional[float]) -> str:
    """Format file size for display."""
    if size_bytes is None or size_bytes == "N/A":
        return "N/A"
    try:
        size_bytes = float(size_bytes)
        if size_bytes == 0:
            return "0.00 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                formatted = f"{size_bytes:.2f} {unit}"
                return formatted
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"
    except (ValueError, TypeError):
        return "N/A"


def validate_url(url: str) -> bool:
    """
    Validate if URL is a valid URL.
    Supports http and https schemes only (secure subset for UI validation).
    Note: yt-dlp may support additional schemes, but UI validation is more restrictive.
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip()

    # Check length
    if len(url) < 10 or len(url) > 2048:
        return False

    # Check for valid scheme (whitelist approach for security)
    # Only http/https for UI validation (more restrictive than yt-dlp capabilities)
    valid_schemes = ("http://", "https://")
    if not url.startswith(valid_schemes):
        return False

    # Basic URL structure validation
    import re
    # Pattern: scheme://domain.tld/path (simplified)
    pattern = r'^https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+$'
    return bool(re.match(pattern, url))


def validate_proxy(proxy: str) -> bool:
    """
    Validate proxy format.
    Expected format: scheme://host:port (e.g., http://proxy.example.com:8080)
    """
    if not proxy or not isinstance(proxy, str):
        return True  # Empty is valid (no proxy)

    proxy = proxy.strip()
    if not proxy:
        return True

    # Must have scheme
    if not proxy.startswith(("http://", "https://", "socks4://", "socks5://")):
        return False

    # Split scheme and rest
    try:
        scheme, rest = proxy.split("://", 1)
        if not rest:
            return False

        # Must have colon for port
        if ":" not in rest:
            return False

        # Basic validation of host:port
        # Handle user:pass@host:port case
        if "@" in rest:
            auth, hostport = rest.rsplit("@", 1)
        else:
            hostport = rest

        if ":" not in hostport:
            return False

        host, port = hostport.rsplit(":", 1)

        # Validate port is numeric and in valid range
        port_num = int(port)
        if port_num < 1 or port_num > 65535:
            return False

        # Host should not be empty
        if not host:
            return False

        return True

    except (ValueError, IndexError):
        return False


def validate_rate_limit(rate_limit: str) -> bool:
    """
    Validate rate limit format (e.g., 50K, 4.2M, 1G).
    Accepts: digits optionally followed by decimal and one unit (K, M, G, T).
    """
    if not rate_limit or not isinstance(rate_limit, str):
        return True  # Empty is valid (no limit)

    rate_limit = rate_limit.strip()
    if not rate_limit:
        return True

    import re
    # Pattern: number with optional decimal, followed by optional SINGLE unit
    pattern = r'^\d+(\.\d+)?[KMGT]?$'
    if not re.match(pattern, rate_limit, re.IGNORECASE):
        return False

    # Additional check: if value is 0, it's pointless but technically valid
    # Extract numeric part
    numeric_part = re.match(r'^\d+(\.\d+)?', rate_limit)
    if numeric_part:
        value = float(numeric_part.group(0))
        if value <= 0:
            return False  # Zero or negative rate limit makes no sense

    return True


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available in the system path."""
    import shutil

    return shutil.which("ffmpeg") is not None


def open_folder(path: str):
    """
    Opens a folder in the system file manager.
    Handles errors gracefully without raising exceptions.

    Returns:
        bool: True if successful, False otherwise
    """
    if not path:
        logger.warning("No path provided to open_folder")
        return False

    try:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            logger.warning(f"Path does not exist: {path}")
            return False

        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

        return True

    except Exception as ex:
        logger.error(f"Failed to open folder {path}: {ex}")
        return False  # Don't raise in UI context
