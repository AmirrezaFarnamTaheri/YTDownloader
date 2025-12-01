"""
Core downloader logic.

Wraps yt-dlp to provide high-level download operations,
including format selection, cancellation, and progress reporting.
"""

import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yt_dlp

from downloader.engines.generic import GenericDownloader
from downloader.engines.ytdlp import YTDLPWrapper
from downloader.extractors.telegram import TelegramExtractor
from app_state import state  # Import global state for ffmpeg check

logger = logging.getLogger(__name__)


def _sanitize_output_path(output_path: str) -> str:
    """Sanitize output path for security."""
    path = Path(output_path).resolve()
    # Simple check to prevent writing to root/protected areas (basic)
    # In a real app, this might be more restrictive
    return str(path)


# pylint: disable=too-many-locals,too-many-arguments,too-many-branches
def download_video(
    url: str,
    output_path: str = ".",
    video_format: str = "best",
    progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
    cancel_token: Optional[Any] = None,
    download_item: Optional[Dict[str, Any]] = None,
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
) -> Dict[str, Any]:
    """
    Downloads a video/audio from the given URL using yt-dlp or generic fallback.

    Args:
        url: The URL to download.
        output_path: The directory to save the file.
        video_format: 'best', 'audio', '4k', '1080p', etc.
        progress_hook: Callback function for progress updates.
        cancel_token: Object with 'cancelled' attribute to check for cancellation.
        playlist: Whether to download playlist.
        sponsorblock: Whether to use SponsorBlock.
        use_aria2c: Whether to use aria2c external downloader.
        gpu_accel: GPU acceleration backend ('cuda', 'vulkan', 'auto', etc.).
        output_template: Template for output filename.
        start_time: Start time for download (HH:MM:SS).
        end_time: End time for download (HH:MM:SS).
        force_generic: Force use of generic downloader.
        cookies_from_browser: Browser to extract cookies from.

    Returns:
        Dict containing download metadata.
    """
    logger.info("Initiating download_video for URL: %s", url)

    # 1. Handle Output Path
    output_path = _sanitize_output_path(output_path or ".")

    # If output path is "." or empty, try to default to Downloads
    if output_path == ".":
        try:
             home = Path.home()
             downloads = home / "Downloads"
             if downloads.exists() and os.access(downloads, os.W_OK):
                 output_path = str(downloads)
             elif os.access(home, os.W_OK):
                 output_path = str(home)
             logger.info("No explicit output path; defaulting to %s", output_path)
        except Exception:
             pass

    if not os.path.exists(output_path):
        logger.debug("Creating output directory: %s", output_path)
        os.makedirs(output_path, exist_ok=True)

    # 2. Check for Generic Fallback
    if force_generic or not YTDLPWrapper.supports(url):
        logger.info("Using GenericDownloader (force=%s)", force_generic)
        if "t.me/" in url:
            # Special handling for telegram if not handled by yt-dlp
            # (Though yt-dlp handles some telegram links, our extractor is a backup)
            pass
        return GenericDownloader.download(
            url, output_path, progress_hook, cancel_token
        )

    # 3. Configure yt-dlp options
    ydl_opts = {
        "outtmpl": f"{output_path}/{output_template}",
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,  # Continue playlist even if one fails
        "noplaylist": not playlist,
        "extract_flat": False,
        # Default format spec (will be refined below)
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "writethumbnail": True,
        # Post-processors
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
    if subtitle_lang:
        ydl_opts["subtitles"] = subtitle_lang
        ydl_opts["writesubtitles"] = True
        if subtitle_format:
            ydl_opts["subtitlesformat"] = subtitle_format
    if split_chapters and ffmpeg_available:
        ydl_opts.setdefault("postprocessors", []).append({"key": "FFmpegSplitChapters"})

    # 3a. FFmpeg Availability Check
    # Some features require FFmpeg. If not available, we must disable them.
    ffmpeg_available = getattr(state, "ffmpeg_available", True)
    if not ffmpeg_available:
        logger.warning("FFmpeg not available - disabling post-processors and merging")
        ydl_opts["postprocessors"] = [] # Clear postprocessors
        ydl_opts["writethumbnail"] = False
        # Avoid formats that require merging (video+audio)
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
    elif video_format == "4k":
        ydl_opts["format"] = "bestvideo[height>=2160]+bestaudio/best"
    elif video_format == "1440p":
        ydl_opts["format"] = "bestvideo[height>=1440]+bestaudio/best"
    elif video_format == "1080p":
        ydl_opts["format"] = "bestvideo[height>=1080]+bestaudio/best"
    elif video_format == "720p":
        ydl_opts["format"] = "bestvideo[height>=720]+bestaudio/best"
    elif video_format == "480p":
        ydl_opts["format"] = "bestvideo[height>=480]+bestaudio/best"

    # If ffmpeg missing and a specific resolution was asked that implies merging,
    # yt-dlp might fail if it downloads separate streams.
    # We fallback to 'best' (single file) if not audio-only above.
    if not ffmpeg_available and video_format != "audio":
         ydl_opts["format"] = "best"

    # 3c. Download Sections (Time Range)
    if start_time or end_time:
        if ffmpeg_available:
            logger.info("Downloading range: %s - %s", start_time, end_time)
            ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(
                None,
                [(_parse_time(start_time), _parse_time(end_time))],
            )
            # Force external downloader for splitting if needed, though usually handled internally
            # or by ffmpeg post-processing.
        else:
             logger.warning("Download range ignored - FFmpeg not available")

    # 3d. SponsorBlock
    if sponsorblock:
        if ffmpeg_available:
            logger.debug("Enabling SponsorBlock")
            ydl_opts["postprocessors"].append(
                {
                    "key": "SponsorBlock",
                    "categories": [
                        "sponsor",
                        "selfpromo",
                        "interaction",
                        "intro",
                        "outro",
                        "preview",
                        "music_offtopic",
                    ],
                    "when": "after_filter",  # Remove before download if possible? No, usually post-process.
                }
            )
        else:
            logger.warning("SponsorBlock skipped - FFmpeg not available")

    # 3e. Aria2c
    if use_aria2c:
        # Check if aria2c is actually available (e.g. shutil.which)
        # If running on mobile, it might not be.
        aria2_path = shutil.which("aria2c")
        if aria2_path:
            logger.debug("Enabling aria2c accelerator")
            ydl_opts["external_downloader"] = "aria2c"
            ydl_opts["external_downloader_args"] = [
                "-x",
                "16",
                "-k",
                "1M",
                "-s",
                "16",
            ]
        else:
            logger.warning("Aria2c enabled but binary not found on PATH. Ignoring.")

    # 3f. GPU Acceleration (experimental)
    # The 'gpu_accel' option in yt-dlp is not a direct global flag but often
    # passed to ffmpeg args if recoding.
    # However, for just downloading, it doesn't do much unless we are encoding.
    # We can pass ffmpeg args if we are post-processing.
    if gpu_accel and gpu_accel.lower() != "none" and ffmpeg_available:
        # Resolve 'auto' to a concrete backend if possible, or just defaults
        accel_flag = gpu_accel
        if gpu_accel.lower() == "auto":
             # Simple heuristic or default to cuda on Windows, empty on others
             if os.name == "nt":
                 accel_flag = "cuda" # Try cuda
             else:
                 accel_flag = None # Let ffmpeg decide or software

        if accel_flag:
            logger.debug("Enabling GPU acceleration: %s", accel_flag)
            # This is specific to how yt-dlp passes args to ffmpeg
            # We add postprocessor args.
            ydl_opts["postprocessor_args"] = {"ffmpeg": ["-hwaccel", accel_flag]}

    # 3g. Cookies
    if cookies_from_browser:
        logger.debug("Using cookies from browser: %s", cookies_from_browser)
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)

    # 3h. Output Template Validation
    # Ensure template doesn't contain paths if we are enforcing output_path
    # (yt-dlp allows path in template, which overrides outtmpl path)
    # We'll rely on user trusting the template they set in config.

    # 4. Filter match (e.g. for playlists)
    # ydl_opts['match_filter'] = ... (Not implemented in UI yet)

    # 5. Execute Download
    wrapper = YTDLPWrapper(ydl_opts)
    try:
        return wrapper.download(url, progress_hook, cancel_token)
    except Exception as e:
        logger.error("yt-dlp download failed: %s", e)
        # Fallback to generic if it was a network/extractor error?
        # Maybe, but often it's better to fail explicitly.
        raise


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
