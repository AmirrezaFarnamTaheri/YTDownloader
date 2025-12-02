"""
Core downloader logic.

Wraps yt-dlp to provide high-level download operations,
including format selection, cancellation, and progress reporting.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import yt_dlp

from downloader.engines.generic import GenericDownloader
from downloader.engines.ytdlp import YTDLPWrapper
from downloader.types import DownloadOptions
from downloader.extractors.telegram import TelegramExtractor
from app_state import state

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
        return str(path)
    except Exception as e:
        logger.warning("Failed to sanitize path '%s': %s", output_path, e)
        return "."


def download_video(options: DownloadOptions) -> Dict[str, Any]:
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
        # Fallback for compatibility or catch errors
        raise TypeError(f"download_video expects DownloadOptions, got {type(options)}")

    logger.info("Initiating download_video for URL: %s", options.url)

    # 1. Validation
    options.validate()

    # 2. Handle Output Path
    output_path = _sanitize_output_path(options.output_path)
    if not os.path.exists(output_path):
        try:
            os.makedirs(output_path, exist_ok=True)
        except OSError as e:
            logger.error("Failed to create output directory: %s", e)
            raise ValueError(f"Invalid output directory: {e}") from e

    # 3a. Check for Telegram
    if TelegramExtractor.is_telegram_url(options.url):
        logger.info("Using TelegramExtractor for: %s", options.url)
        return TelegramExtractor.extract(
            options.url,
            output_path,
            options.progress_hook,
            options.cancel_token
        )

    # 3b. Check for Generic Fallback
    if options.force_generic or not YTDLPWrapper.supports(options.url):
        logger.info("Using GenericDownloader (force=%s)", options.force_generic)
        return GenericDownloader.download(
            options.url,
            output_path,
            options.progress_hook,
            options.cancel_token
        )

    # 4. Configure yt-dlp options
    ydl_opts = {
        "outtmpl": f"{output_path}/{options.output_template}",
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "noplaylist": not options.playlist,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "writethumbnail": True,
        "postprocessors": [
            {"key": "FFmpegEmbedSubtitle"},
            {"key": "EmbedThumbnail"},
            {"key": "FFmpegMetadata"},
        ],
    }

    if options.proxy:
        ydl_opts["proxy"] = options.proxy
    if options.rate_limit:
        ydl_opts["ratelimit"] = options.rate_limit

    # 4a. FFmpeg Availability Check
    ffmpeg_available = getattr(state, "ffmpeg_available", True)

    if options.subtitle_lang:
        ydl_opts["subtitles"] = options.subtitle_lang
        ydl_opts["writesubtitles"] = True
        if options.subtitle_format:
            ydl_opts["subtitlesformat"] = options.subtitle_format

    if options.split_chapters and ffmpeg_available:
        ydl_opts.setdefault("postprocessors", []).append({"key": "FFmpegSplitChapters"})

    if not ffmpeg_available:
        logger.warning("FFmpeg not available - disabling post-processors and merging")
        ydl_opts["postprocessors"] = []
        ydl_opts["writethumbnail"] = False
        ydl_opts["format"] = "best"
        ydl_opts.pop("merge_output_format", None)

    # 4b. Format Selection
    if options.video_format == "audio":
        ydl_opts["format"] = "bestaudio/best"
        if ffmpeg_available:
            # Whitelist supported codecs
            allowed_codecs = {"mp3", "m4a", "wav", "flac", "opus"}
            codec = (options.audio_format or "mp3").lower()
            if codec not in allowed_codecs:
                codec = "mp3"

            ydl_opts["postprocessors"].append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": codec,
                    "preferredquality": "192" if codec in {"mp3", "m4a", "opus"} else None,
                }
            )
            # Remove None values
            ydl_opts["postprocessors"][-1] = {
                k: v for k, v in ydl_opts["postprocessors"][-1].items() if v is not None
            }
    elif options.video_format in ["4k", "1440p", "1080p", "720p", "480p"]:
        height_map = {
            "4k": 2160, "1440p": 1440, "1080p": 1080, "720p": 720, "480p": 480
        }
        h = height_map.get(options.video_format, 1080)
        ydl_opts["format"] = f"bestvideo[height>={h}]+bestaudio/best"

    if not ffmpeg_available and options.video_format != "audio":
        ydl_opts["format"] = "best"

    # 4c. Download Sections (Time Range)
    if (options.start_time or options.end_time) and ffmpeg_available:
        start_sec = options._parse_time(options.start_time)
        end_sec = options._parse_time(options.end_time)
        logger.info("Downloading range: %s - %s", options.start_time, options.end_time)
        ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(
            None, [(start_sec, end_sec)]
        )

    # 4d. SponsorBlock
    if options.sponsorblock and ffmpeg_available:
        ydl_opts["postprocessors"].append(
            {
                "key": "SponsorBlock",
                "categories": ["sponsor", "selfpromo", "interaction", "intro", "outro"],
                "when": "after_filter",
            }
        )

    # 4e. Aria2c
    if options.use_aria2c:
        if shutil.which("aria2c"):
            ydl_opts["external_downloader"] = "aria2c"
            ydl_opts["external_downloader_args"] = ["-x", "16", "-k", "1M", "-s", "16"]
        else:
            logger.warning("Aria2c enabled but not found.")

    # 4f. GPU Acceleration
    if options.gpu_accel and options.gpu_accel.lower() != "none" and ffmpeg_available:
        accel_flag = options.gpu_accel
        if options.gpu_accel.lower() == "auto":
            accel_flag = "cuda" if os.name == "nt" else None

        if accel_flag:
            ydl_opts["postprocessor_args"] = {"ffmpeg": ["-hwaccel", accel_flag]}

    # 4g. Cookies
    if options.cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (options.cookies_from_browser,)

    wrapper = YTDLPWrapper(ydl_opts)
    try:
        return wrapper.download(
            options.url,
            options.progress_hook,
            options.cancel_token,
            download_item=options.download_item,
            output_path=output_path
        )
    except Exception as e:
        logger.error("yt-dlp download failed: %s", e)
        raise
