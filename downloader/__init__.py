"""
Downloader module.

This package provides download functionality including:
- Core download logic
- yt-dlp integration
- Generic HTTP downloader with resume support
- Platform-specific extractors (Telegram, etc.)
"""

from downloader.core import download_video
from downloader.info import get_video_info
from downloader.types import DownloadOptions

__all__ = [
    "download_video",
    "get_video_info",
    "DownloadOptions",
]
