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


def _validate_proxy_host(hostname: str) -> None:
    """Reject loopback/private/reserved proxy hosts and malformed numeric IPs.

    Raises:
        ValueError: when the host is unsafe or malformed.
    """
    if len(hostname) > 253:
        raise ValueError("Invalid proxy hostname")

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError as exc:
        # Not an IP literal: reject malformed dotted-quad strings, accept DNS names
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", hostname):
            raise ValueError("Invalid proxy host IP") from exc
        return

    unsafe_flags = (
        ip.is_multicast,
        ip.is_unspecified,
        ip.is_reserved,
        ip.is_loopback,
        ip.is_link_local,
        ip.is_private,
    )
    if any(unsafe_flags):
        raise ValueError("Proxy must use a public host (no localhost/private/loopback)")


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
    download_profile: str | None = None
    download_item: dict[str, Any] | None = None
    filename: str | None = None
    no_check_certificate: bool = False

    def validate(self):
        """Perform validation on the options."""
        self._validate_proxy()
        self._validate_time()
        self._validate_filename()

    def _validate_proxy(self):
        """Validate proxy settings (scheme, host shape, port)."""
        if self.proxy:
            try:
                parsed = urlparse(self.proxy)
                if not parsed.scheme or not parsed.scheme.startswith(("http", "socks")):
                    raise ValueError(
                        "Invalid proxy URL. Must start with http/https/socks"
                    )

                hostname = parsed.hostname
                if not hostname:
                    raise ValueError("Proxy must include a hostname")

                _validate_proxy_host(hostname)

                if parsed.port is not None and not 1 <= parsed.port <= 65535:
                    raise ValueError("Proxy port must be in range 1-65535")
            except ValueError as e:
                raise ValueError(str(e)) from e
            except Exception as e:
                raise ValueError(f"Invalid proxy configuration: {e}") from e

    def _validate_time(self):
        """Validate time range settings.

        - Both empty: OK (no section trimming).
        - Only start_time: download from start_time to end-of-video.
        - Only end_time: download from beginning to end_time.
        - Both: require start < end.
        """
        start_sec = self.get_seconds(self.start_time)
        end_sec = self.get_seconds(self.end_time)

        if start_sec < 0 or end_sec < 0:
            raise ValueError("Time values must be non-negative")

        # Only enforce ordering when both are explicitly provided
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
    split_chapters: bool
    insta_type: str | None
    proxy: str | None
    rate_limit: str | None
    download_profile: str | None
    # Internal
    filepath: str
    filename: str
    control_ref: Any  # weakref to UI control
    _allocated_at: datetime
    _was_queued: bool
