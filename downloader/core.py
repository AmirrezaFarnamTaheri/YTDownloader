"""
Core downloader logic.

Wraps yt-dlp to provide high-level download operations,
including format selection, cancellation, and progress reporting.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yt_dlp

from downloader.engines.generic import GenericDownloader
from downloader.engines.ytdlp import YTDLPWrapper
from downloader.extractors.telegram import TelegramExtractor
from downloader.types import DownloadOptions

logger = logging.getLogger(__name__)


def _sanitize_output_path(output_path: str) -> str:
    """
    Sanitize output path for security and correctness.
    Ensures the path is absolute and resolves to a writable location.
    """
    try:
        if not output_path or output_path == ".":
            return str(Path.cwd())

        path = Path(output_path).resolve()

        # Verify write permissions
        if path.exists():
            if not os.access(path, os.W_OK):
                logger.warning(
                    "No write permission for path '%s', falling back to temp", path
                )
                return tempfile.gettempdir()
        else:
            # Try to create it, if fails, fallback
            os.makedirs(path, exist_ok=True)

        return str(path)
    except (OSError, TypeError, ValueError) as e:
        logger.warning("Failed to sanitize path '%s': %s", output_path, e)
        return tempfile.gettempdir()


def _check_disk_space(output_path: str, min_mb: int = 100) -> bool:
    """Check if there is sufficient disk space."""
    try:
        usage = shutil.disk_usage(output_path)
        free_mb = usage.free / (1024 * 1024)
        if free_mb < min_mb:
            logger.warning("Low disk space: %.2f MB free", free_mb)
            # We don't block, but we log loud
            return False
        return True
    except (OSError, ValueError) as e:
        logger.error("Failed to check disk space: %s", e)
        return True  # Assume ok if check fails


def _configure_postprocessors(
    ydl_opts: dict[str, Any], options: DownloadOptions, ffmpeg_available: bool
) -> None:
    """Configure yt-dlp postprocessors based on options."""
    # Ensure postprocessors list exists
    if "postprocessors" not in ydl_opts:
        ydl_opts["postprocessors"] = []

    # Default postprocessors
    if ffmpeg_available:
        ydl_opts["postprocessors"].extend(
            [
                {"key": "FFmpegEmbedSubtitle"},
                {"key": "EmbedThumbnail"},
                {"key": "FFmpegMetadata"},
            ]
        )
    else:
        logger.warning("FFmpeg not available - disabling post-processors and merging")
        ydl_opts["postprocessors"] = []
        ydl_opts["writethumbnail"] = False
        ydl_opts["format"] = "best"
        ydl_opts.pop("merge_output_format", None)
        return

    # Split chapters
    if options.split_chapters:
        ydl_opts["postprocessors"].append({"key": "FFmpegSplitChapters"})

    # SponsorBlock
    if options.sponsorblock:
        ydl_opts["postprocessors"].append(
            {
                "key": "SponsorBlock",
                "categories": ["sponsor", "selfpromo", "interaction", "intro", "outro"],
                "when": "after_filter",
            }
        )


def _configure_format_selection(
    ydl_opts: dict[str, Any], options: DownloadOptions, ffmpeg_available: bool
) -> None:
    """Configure format selection options."""
    if options.video_format == "audio":
        ydl_opts["format"] = "bestaudio/best"
        if ffmpeg_available:
            # Whitelist supported codecs
            allowed_codecs = {"mp3", "m4a", "wav", "flac", "opus"}
            codec = (options.audio_format or "mp3").lower()
            if codec not in allowed_codecs:
                codec = "mp3"

            pp_args = {
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
            }
            if codec in {"mp3", "m4a", "opus"}:
                pp_args["preferredquality"] = "192"

            ydl_opts.setdefault("postprocessors", []).append(pp_args)
        return

    if not ffmpeg_available and options.video_format != "audio":
        ydl_opts["format"] = "best"
        return

    if options.video_format in ["4k", "1440p", "1080p", "720p", "480p"]:
        height_map = {
            "4k": 2160,
            "1440p": 1440,
            "1080p": 1080,
            "720p": 720,
            "480p": 480,
        }
        h = height_map.get(options.video_format, 1080)
        # Prefer best at or below target height; if none, allow closest above.
        # Fall back to overall best to avoid hard failures.
        ydl_opts["format"] = (
            f"bestvideo[height<={h}]+bestaudio/best/"
            f"bestvideo[height>={h}]+bestaudio/best/"
            f"best"
        )
    else:
        # Explicit format id selection or best + custom audio
        if options.video_format and options.video_format != "best":
            if options.audio_format:
                ydl_opts["format"] = (
                    f"{options.video_format}+{options.audio_format}/best"
                )
            else:
                ydl_opts["format"] = options.video_format
        elif options.audio_format:
            ydl_opts["format"] = f"bestvideo+{options.audio_format}/best"


def _configure_advanced_options(
    ydl_opts: dict[str, Any], options: DownloadOptions, ffmpeg_available: bool
) -> None:
    """Configure advanced download options."""
    # Proxy and Rate Limit
    if options.proxy:
        ydl_opts["proxy"] = options.proxy
    if options.rate_limit:
        ydl_opts["ratelimit"] = options.rate_limit

    # Subtitles
    if options.subtitle_lang:
        ydl_opts["subtitles"] = options.subtitle_lang
        # yt-dlp expects a list for subtitleslangs
        ydl_opts["subtitleslangs"] = [options.subtitle_lang]
        ydl_opts["writesubtitles"] = True
        if options.subtitle_format:
            ydl_opts["subtitlesformat"] = options.subtitle_format

    # Download Sections (Time Range)
    if (options.start_time or options.end_time) and ffmpeg_available:
        start_sec = (
            int(options.get_seconds(options.start_time)) if options.start_time else 0
        )
        end_sec = (
            int(options.get_seconds(options.end_time)) if options.end_time else None
        )
        logger.info("Downloading range: %s - %s", options.start_time, options.end_time)
        ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(
            [], [(start_sec, end_sec)]  # type: ignore[arg-type,list-item]
        )

    # Aria2c
    if options.use_aria2c:
        if shutil.which("aria2c"):
            ydl_opts["external_downloader"] = "aria2c"
            ydl_opts["external_downloader_args"] = ["-x", "16", "-k", "1M", "-s", "16"]
        else:
            logger.warning("Aria2c enabled but not found.")

    # GPU Acceleration
    if options.gpu_accel and options.gpu_accel.lower() != "none" and ffmpeg_available:
        accel_flag: str | None = options.gpu_accel
        if options.gpu_accel.lower() == "auto":
            accel_flag = "cuda" if os.name == "nt" else None

        if accel_flag:
            ydl_opts["postprocessor_args"] = {"ffmpeg": ["-hwaccel", accel_flag]}

    # Cookies - yt-dlp expects a 2-tuple: (browser_name, profile_name)
    if options.cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (options.cookies_from_browser, None)


def download_video(options: DownloadOptions) -> dict[str, Any]:
    """
    Downloads a video/audio from the given URL using yt-dlp or generic fallback.

    Args:
        options: A DownloadOptions object containing all parameters.

    Returns:
        Dict containing download status and metadata.

    Raises:
        ValueError: If validation fails.
        Exception: If download fails.
    """
    # Guard against incorrect usage (e.g. legacy kwargs)
    if not isinstance(options, DownloadOptions):
        raise TypeError(f"download_video expects DownloadOptions, got {type(options)}")

    logger.info("Initiating download_video for URL: %s", options.url)

    # 1. Validation
    options.validate()

    # Sanitize output_template to prevent path traversal
    # It should not be absolute and should not contain '..' segments
    if os.path.isabs(options.output_template):
        raise ValueError("Output template must be a relative path")

    # Disallow any directory separators to ensure it's just a filename template
    if os.path.sep in options.output_template or (
        os.path.altsep and os.path.altsep in options.output_template
    ):
        raise ValueError("Output template cannot contain path separators ('/' or '\\')")

    # Check for '..' segments
    normalized_path = os.path.normpath(options.output_template)
    if ".." in normalized_path.split(os.path.sep):
        raise ValueError(
            "Output template must not contain parent directory references ('..')"
        )

    # 2. Handle Output Path
    output_path = _sanitize_output_path(options.output_path)
    if not os.path.exists(output_path):
        try:
            os.makedirs(output_path, exist_ok=True)
        except OSError as e:
            logger.error("Failed to create output directory: %s", e)
            raise ValueError(f"Invalid output directory: {e}") from e

    if not _check_disk_space(output_path):
        raise OSError("Not enough disk space on the target device.")

    # 3a. Check for Telegram
    if TelegramExtractor.is_telegram_url(options.url):
        logger.info("Using TelegramExtractor for: %s", options.url)
        return TelegramExtractor.extract(
            options.url, output_path, options.progress_hook, options.cancel_token
        )

    # 3b. Check for Generic Fallback
    if options.force_generic or not YTDLPWrapper.supports(options.url):
        logger.info("Using GenericDownloader (force=%s)", options.force_generic)
        return GenericDownloader.download(
            options.url,
            output_path,
            options.progress_hook,
            options.cancel_token,
            filename=options.filename,
        )

    # 4. Configure yt-dlp options
    outtmpl_path = str(Path(output_path) / options.output_template)
    ydl_opts: dict[str, Any] = {
        "outtmpl": outtmpl_path,
        "quiet": True,
        "no_warnings": True,
        # SECURITY: Verify SSL certificates by default - only disable if explicitly requested
        "nocheckcertificate": (
            options.no_check_certificate
            if hasattr(options, "no_check_certificate")
            else False
        ),
        "ignoreerrors": True,
        "noplaylist": not options.playlist,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "writethumbnail": True,
    }

    logger.debug("yt-dlp outtmpl resolved to: %s", outtmpl_path)

    # 4a. Check FFmpeg availability
    # Check directly instead of relying on global state
    ffmpeg_available = shutil.which("ffmpeg") is not None

    # 4b. Configure Post-processors
    _configure_postprocessors(ydl_opts, options, ffmpeg_available)

    # 4c. Configure Format Selection
    _configure_format_selection(ydl_opts, options, ffmpeg_available)

    # 4d. Configure Advanced Options
    _configure_advanced_options(ydl_opts, options, ffmpeg_available)

    wrapper = YTDLPWrapper(ydl_opts)
    try:
        return wrapper.download(
            options.url,
            options.progress_hook,
            options.cancel_token,
            download_item=options.download_item,
            output_path=output_path,
        )
    except Exception as e:
        logger.error("yt-dlp download failed: %s", e)
        raise
