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
    """Validate if URL is a valid video URL."""
    url = url.strip()
    valid = url.startswith(("http://", "https://")) and len(url) > 10
    return valid


def validate_proxy(proxy: str) -> bool:
    """Validate proxy format."""
    if not proxy.strip():
        return True  # Empty is valid (no proxy)
    # Basic proxy validation: should contain :// and have a host:port
    valid = "://" in proxy and ":" in proxy.split("://", 1)[1]
    return valid


def validate_rate_limit(rate_limit: str) -> bool:
    """Validate rate limit format (e.g., 50K, 4.2M)."""
    if not rate_limit.strip():
        return True  # Empty is valid (no limit)
    import re

    valid = bool(re.match(r"^\d+(\.\d+)?[KMGT]?$", rate_limit.strip()))
    return valid


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available in the system path."""
    import shutil

    return shutil.which("ffmpeg") is not None

def open_folder(path: str):
    """Opens a folder in the system file manager."""
    if not path:
        return
    try:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            logger.warning(f"Path does not exist: {path}")
            return

        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as ex:
        logger.error(f"Failed to open folder {path}: {ex}")
        raise ex
