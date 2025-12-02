"""
Core downloader logic.

Wraps yt-dlp to provide high-level download operations,
including format selection, cancellation, and progress reporting.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yt_dlp

from downloader.engines.generic import GenericDownloader
from downloader.engines.ytdlp import YTDLPWrapper
from app_state import state

logger = logging.getLogger(__name__)


def _sanitize_output_path(output_path: str) -> str:
    """
    Sanitize output path for security and correctness.
    Ensures the path is absolute and resolves to a writable location.
    """
    try:
        if not output_path or output_path == ".":
            # Default logic handled outside, but just in case
            return str(Path.cwd())

        path = Path(output_path).resolve()
        return str(path)
    except Exception as e:
        logger.warning("Failed to sanitize path '%s': %s", output_path, e)
        return "."


def _parse_time(time_str: Optional[str]) -> float:
    """Parse HH:MM:SS to seconds."""
    if not time_str:
        return 0.0
    try:
        parts = list(map(int, time_str.split(":")))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return float(parts[0])
    except ValueError:
        return 0.0


# pylint: disable=too-many-locals,too-many-arguments,too-many-branches
def download_video(
    url: str,
    output_path: str = ".",
    video_format: str = "best",
    progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
    cancel_token: Optional[Any] = None,
    playlist: bool = False,
    sponsorblock: bool = False,
    use_aria2c: bool = False,
    gpu_accel: Optional[str] = None,
    output_template: str = "%(title)s.%(ext)s",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    force_generic: bool = False,
    cookies_from_browser: Optional[str] = None,
    subtitle_lang: Optional[str] = None,
    subtitle_format: Optional[str] = None,
    split_chapters: bool = False,
    proxy: Optional[str] = None,
    rate_limit: Optional[str] = None,
    **kwargs: Any,  # Accept extra arguments for compatibility (e.g. download_item)
) -> Dict[str, Any]:
    """
    Downloads a video/audio from the given URL using yt-dlp or generic fallback.
    """
    logger.info("Initiating download_video for URL: %s", url)

    # 1. Handle Output Path
    output_path = _sanitize_output_path(output_path)
    if not os.path.exists(output_path):
        try:
            os.makedirs(output_path, exist_ok=True)
        except OSError as e:
            logger.error("Failed to create output directory: %s", e)
            raise ValueError(f"Invalid output directory: {e}")

    # 2. Check for Generic Fallback
    if proxy and not (proxy.startswith("http") or proxy.startswith("socks")):
        raise ValueError("Invalid proxy URL. Must start with http/https/socks")

    start_sec = _parse_time(start_time)
    end_sec = _parse_time(end_time)
    if start_sec < 0 or end_sec < 0:
        raise ValueError("Time values must be non-negative")
    if start_time and end_time and start_sec >= end_sec:
         raise ValueError("Start time must be before end time")

    if force_generic or not YTDLPWrapper.supports(url):
        logger.info("Using GenericDownloader (force=%s)", force_generic)
        return GenericDownloader.download(
            url, output_path, progress_hook, cancel_token
        )

    # 3. Configure yt-dlp options
    ydl_opts = {
        "outtmpl": f"{output_path}/{output_template}",
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "noplaylist": not playlist,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "writethumbnail": True,
        "postprocessors": [
            {"key": "FFmpegEmbedSubtitle"},
            {"key": "EmbedThumbnail"},
            {"key": "FFmpegMetadata"},
        ],
    }

    if proxy:
        ydl_opts["proxy"] = proxy
    if rate_limit:
        ydl_opts["ratelimit"] = rate_limit

    # 3a. FFmpeg Availability Check
    ffmpeg_available = getattr(state, "ffmpeg_available", True)

    if subtitle_lang:
        ydl_opts["subtitles"] = subtitle_lang
        ydl_opts["writesubtitles"] = True
        if subtitle_format:
            ydl_opts["subtitlesformat"] = subtitle_format

    if split_chapters and ffmpeg_available:
        ydl_opts.setdefault("postprocessors", []).append({"key": "FFmpegSplitChapters"})

    if not ffmpeg_available:
        logger.warning("FFmpeg not available - disabling post-processors and merging")
        ydl_opts["postprocessors"] = []
        ydl_opts["writethumbnail"] = False
        ydl_opts["format"] = "best"
        ydl_opts.pop("merge_output_format", None)

    # 3b. Format Selection
    if video_format == "audio":
        ydl_opts["format"] = "bestaudio/best"
        if ffmpeg_available:
            ydl_opts["postprocessors"].append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            )
    elif video_format in ["4k", "1440p", "1080p", "720p", "480p"]:
        height_map = {
            "4k": 2160, "1440p": 1440, "1080p": 1080, "720p": 720, "480p": 480
        }
        h = height_map.get(video_format, 1080)
        ydl_opts["format"] = f"bestvideo[height>={h}]+bestaudio/best"

    if not ffmpeg_available and video_format != "audio":
         ydl_opts["format"] = "best"

    # 3c. Download Sections (Time Range)
    if (start_time or end_time) and ffmpeg_available:
        logger.info("Downloading range: %s - %s", start_time, end_time)
        ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(
            None, [(_parse_time(start_time), _parse_time(end_time))]
        )

    # 3d. SponsorBlock
    if sponsorblock and ffmpeg_available:
        ydl_opts["postprocessors"].append(
            {
                "key": "SponsorBlock",
                "categories": ["sponsor", "selfpromo", "interaction", "intro", "outro"],
                "when": "after_filter",
            }
        )

    # 3e. Aria2c
    if use_aria2c:
        if shutil.which("aria2c"):
            ydl_opts["external_downloader"] = "aria2c"
            ydl_opts["external_downloader_args"] = ["-x", "16", "-k", "1M", "-s", "16"]
        else:
            logger.warning("Aria2c enabled but not found.")

    # 3f. GPU Acceleration
    if gpu_accel and gpu_accel.lower() != "none" and ffmpeg_available:
        accel_flag = gpu_accel
        if gpu_accel.lower() == "auto":
             accel_flag = "cuda" if os.name == "nt" else None

        if accel_flag:
            ydl_opts["postprocessor_args"] = {"ffmpeg": ["-hwaccel", accel_flag]}

    # 3g. Cookies
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)

    wrapper = YTDLPWrapper(ydl_opts)
    try:
        return wrapper.download(url, progress_hook, cancel_token)
    except Exception as e:
        logger.error("yt-dlp download failed: %s", e)
        raise
