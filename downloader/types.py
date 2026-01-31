"""
Configuration dataclasses and type definitions for the downloader.
"""

import ipaddress
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Literal, TypedDict
from urllib.parse import urlparse


class DownloadStatus(str, Enum):
    """Enumeration of possible download statuses."""

    QUEUED = "Queued"
    ALLOCATING = "Allocating"
    DOWNLOADING = "Downloading"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    ERROR = "Error"
    CANCELLED = "Cancelled"
    PAUSED = "Paused"
    SCHEDULED = "Scheduled"

    def __str__(self):
        return self.value


@dataclass
# pylint: disable=too-many-instance-attributes
class DownloadOptions:
    """Options for controlling the download process."""

    url: str
    output_path: str = "."
    video_format: str = "best"
    audio_format: str | None = None
    progress_hook: Callable[[dict[str, Any]], None] | None = None
    cancel_token: Any | None = None
    playlist: bool = False
    sponsorblock: bool = False
    use_aria2c: bool = False
    gpu_accel: str | None = None
    output_template: str = "%(title)s.%(ext)s"
    start_time: str | None = None
    end_time: str | None = None
    force_generic: bool = False
    cookies_from_browser: str | None = None
    subtitle_lang: str | None = None
    subtitle_format: str | None = None
    split_chapters: bool = False
    proxy: str | None = None
    rate_limit: str | None = None
    download_item: dict[str, Any] | None = None
    filename: str | None = None
    no_check_certificate: bool = False

    def validate(self):
        """Perform validation on the options."""
        self._validate_proxy()
        self._validate_time()
        self._validate_filename()

    def _validate_proxy(self):
        """Validate proxy settings."""
        if self.proxy:
            try:
                parsed = urlparse(self.proxy)
                if not parsed.scheme or not parsed.scheme.startswith(("http", "socks")):
                    raise ValueError(
                        "Invalid proxy URL. Must start with http/https/socks"
                    )

                hostname = parsed.hostname
                if hostname:
                    if hostname in ("localhost", "127.0.0.1", "::1"):
                        raise ValueError("Local proxies are not allowed")
                    try:
                        ip = ipaddress.ip_address(hostname)
                        if ip.is_private or ip.is_loopback:
                            raise ValueError("Private IP proxies are not allowed")
                    except ValueError:
                        # Simple regex check for IP-like strings that failed ip_address check
                        # This prevents "1.2.3.999" from bypassing if it wasn't caught above
                        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", hostname):
                            raise ValueError("Invalid proxy host IP") from None
            except ValueError as e:
                raise ValueError(str(e)) from e
            except Exception as e:
                raise ValueError(f"Invalid proxy configuration: {e}") from e

    def _validate_time(self):
        """Validate time range settings."""
        start_sec = self.get_seconds(self.start_time)
        end_sec = self.get_seconds(self.end_time)

        if start_sec < 0 or end_sec < 0:
            raise ValueError("Time values must be non-negative")

        if self.start_time and self.end_time and start_sec >= end_sec:
            raise ValueError("Start time must be before end time")

    def _validate_filename(self):
        """Validate filename settings."""
        if self.filename:
            if "\x00" in self.filename:
                raise ValueError("Filename must not contain null bytes")
            if re.search(r"[/\\]", self.filename):
                raise ValueError("Filename must not contain path separators")
            if self.filename in (".", ".."):
                raise ValueError("Invalid filename")

    @staticmethod
    def get_seconds(time_str: str | None) -> float:
        """Public method to parse time string."""
        return DownloadOptions._parse_time(time_str)

    @staticmethod
    def _parse_time(time_str: str | None) -> float:
        """
        Parse time string (HH:MM:SS or seconds) to seconds.
        Raises ValueError for invalid formats.
        """
        if not time_str:
            return 0.0

        try:
            # First, try to parse as a simple number (seconds).
            return float(time_str)
        except ValueError:
            # If that fails, try to parse HH:MM:SS format.
            try:
                parts = list(map(int, time_str.split(":")))
                if len(parts) == 3:
                    return float(parts[0] * 3600 + parts[1] * 60 + parts[2])
                if len(parts) == 2:
                    return float(parts[0] * 60 + parts[1])

                # Any other number of parts is invalid for HH:MM:SS format.
                # pylint: disable=raise-missing-from
                raise ValueError(f"Invalid time format: {time_str}")
            except (ValueError, TypeError) as e:
                raise ValueError(f"Could not parse time string: {time_str}") from e


class DownloadResult(TypedDict, total=False):
    """
    Type definition for the result of a download operation.
    """

    filename: str
    filepath: str
    url: str
    title: str
    duration: float | None
    thumbnail: str | None
    uploader: str | None
    size: int | float
    type: Literal["video", "playlist", "audio"]
    entries: int  # For playlists


class QueueItem(TypedDict, total=False):
    """
    Type definition for an item in the download queue.
    Using total=False to allow for optional fields during creation.
    """

    id: str
    url: str
    title: str
    status: (
        Literal[
            "Queued",
            "Allocating",
            "Downloading",
            "Processing",
            "Completed",
            "Error",
            "Cancelled",
            "Paused",
        ]
        | DownloadStatus
    )
    scheduled_time: datetime | None
    progress: float
    speed: str
    eta: str
    size: str
    error: str | None
    # Options
    output_path: str
    output_template: str
    video_format: str
    audio_format: str | None
    subtitle_lang: str | None
    playlist: bool
    sponsorblock: bool
    use_aria2c: bool
    gpu_accel: str | None
    start_time: str | None
    end_time: str | None
    force_generic: bool
    cookies_from_browser: str | None
    chapters: bool
    insta_type: str | None
    proxy: str | None
    rate_limit: str | None
    # Internal
    filepath: str
    filename: str
    control_ref: Any  # weakref to UI control
    _allocated_at: datetime
    _was_queued: bool
