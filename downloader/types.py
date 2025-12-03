"""
Configuration dataclasses for the downloader.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class DownloadOptions:
    """Options for controlling the download process."""

    url: str
    output_path: str = "."
    video_format: str = "best"
    audio_format: Optional[str] = None
    progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None
    cancel_token: Optional[Any] = None
    playlist: bool = False
    sponsorblock: bool = False
    use_aria2c: bool = False
    gpu_accel: Optional[str] = None
    output_template: str = "%(title)s.%(ext)s"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    force_generic: bool = False
    cookies_from_browser: Optional[str] = None
    subtitle_lang: Optional[str] = None
    subtitle_format: Optional[str] = None
    split_chapters: bool = False
    proxy: Optional[str] = None
    rate_limit: Optional[str] = None
    download_item: Optional[Dict[str, Any]] = None
    filename: Optional[str] = None

    def validate(self):
        """Perform validation on the options."""
        if self.proxy and not (
            self.proxy.startswith("http") or self.proxy.startswith("socks")
        ):
            raise ValueError("Invalid proxy URL. Must start with http/https/socks")

        start_sec = self.get_seconds(self.start_time)
        end_sec = self.get_seconds(self.end_time)

        if start_sec < 0 or end_sec < 0:
            raise ValueError("Time values must be non-negative")

        if self.start_time and self.end_time and start_sec >= end_sec:
            raise ValueError("Start time must be before end time")

    def get_seconds(self, time_str: Optional[str]) -> float:
        """Public method to parse time string."""
        return self._parse_time(time_str)

    @staticmethod
    def _parse_time(time_str: Optional[str]) -> float:
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
                raise ValueError(f"Invalid time format: {time_str}")
            except (ValueError, TypeError) as e:
                raise ValueError(f"Could not parse time string: {time_str}") from e
