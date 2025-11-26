import os
import logging
from typing import Dict, Any, Callable, Optional, TYPE_CHECKING
from pathlib import Path
from typing import Optional as _OptionalStr

from downloader.extractors.telegram import TelegramExtractor
from downloader.extractors.generic import GenericExtractor
from downloader.engines.generic import download_generic
from downloader.engines.ytdlp import YTDLPWrapper
from downloader.info import get_video_info

if TYPE_CHECKING:
    from utils import CancelToken

logger = logging.getLogger(__name__)


def _sanitize_output_path(base_path: str) -> str:
    """
    Basic normalization for output paths.

    We keep relative paths as-is (so tests and callers that expect "." remain
    compatible) but still normalize empty/None values to the current directory.
    """
    return base_path or "."


def _sanitize_template(template: _OptionalStr[str]) -> _OptionalStr[str]:
    """
    Very lightweight validation for the output template.

    We only forbid path traversal markers that would obviously break out of
    the intended directory; yt-dlp still performs its own parsing/validation.
    """
    if not template:
        return template
    if ".." in template.replace("\\", "/"):
        raise ValueError("Output template must not contain '..' segments")
    return template


def download_video(
    url: str,
    progress_hook: Callable,
    download_item: Dict[str, Any],
    playlist: bool = False,
    video_format: str = "best",
    output_path: str = ".",
    subtitle_lang: Optional[str] = None,
    subtitle_format: str = "srt",
    split_chapters: bool = False,
    proxy: Optional[str] = None,
    rate_limit: Optional[str] = None,
    cancel_token: Optional["CancelToken"] = None,
    cookies_from_browser: Optional[str] = None,
    cookies_from_browser_profile: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    match_filter: Optional[str] = None,
    output_template: Optional[str] = None,
    add_metadata: bool = False,
    embed_thumbnail: bool = False,
    recode_video: Optional[str] = None,
    sponsorblock_remove: bool = False,
    use_aria2c: bool = False,
    gpu_accel: Optional[str] = None,
    force_generic: bool = False,
) -> None:
    """
    Downloads a video or playlist.
    Dispatches to specialized downloaders if needed.
    """
    # Sanitize and ensure output path exists
    output_path = _sanitize_output_path(output_path or ".")
    Path(output_path).mkdir(parents=True, exist_ok=True)

    # Check for hints in download_item or detect
    is_telegram = (download_item or {}).get(
        "is_telegram"
    ) or TelegramExtractor.is_telegram_url(url)

    if force_generic:
        logger.info("Force Generic Mode enabled. Bypassing yt-dlp extraction.")
        info = GenericExtractor.extract(url)
        if info and info.get("video_streams"):
            direct_url = info["video_streams"][0]["url"]
            ext = info["video_streams"][0]["ext"]
            title = info["title"]
            # Be case-insensitive when checking for existing extension
            if not title.lower().endswith(f".{ext.lower()}"):
                filename = f"{title}.{ext}"
            else:
                filename = title

            logger.info("Downloading Generic file (Forced): %s", filename)
            download_generic(
                direct_url,
                output_path,
                filename,
                progress_hook,
                download_item,
                cancel_token,
            )
            return
        logger.warning("Force Generic failed. Falling back to yt-dlp...")

    # Telegram Handling (only when not forcing generic)
    if is_telegram and not force_generic:
        info = TelegramExtractor.extract(url)
        if info and info.get("video_streams"):
            direct_url = info["video_streams"][0]["url"]
            ext = info["video_streams"][0]["ext"]
            title = info["title"]
            filename = f"{title}.{ext}"

            logger.info("Downloading Telegram media: %s", filename)
            download_generic(
                direct_url,
                output_path,
                filename,
                progress_hook,
                download_item,
                cancel_token,
            )
            return

        raise Exception("Could not extract Telegram media")

    # Build yt-dlp Options
    if output_template:
        tmpl = _sanitize_template(output_template)
        outtmpl = os.path.join(output_path, tmpl)
    else:
        outtmpl = os.path.join(output_path, "%(title)s.%(ext)s")

    ydl_opts: Dict[str, Any] = {
        "format": video_format,
        "playlist": playlist,
        "outtmpl": outtmpl,
        "continuedl": True,
        "retries": 10,
        "fragment_retries": 10,
        "quiet": False,
        "no_warnings": False,
        "noplaylist": not playlist,
    }

    if match_filter:
        ydl_opts["match_filter"] = match_filter

    if use_aria2c:
        ydl_opts["external_downloader"] = "aria2c"
        ydl_opts["external_downloader_args"] = ["-x", "16", "-s", "16", "-k", "1M"]

    if subtitle_lang:
        ydl_opts.update(
            {
                "writesubtitles": True,
                "subtitleslangs": [subtitle_lang],
                "subtitlesformat": subtitle_format,
            }
        )

    if split_chapters:
        ydl_opts["split_chapters"] = True
        ydl_opts["outtmpl"] = os.path.join(
            output_path, "%(title)s", "%(section_number)02d - %(section_title)s.%(ext)s"
        )

    if start_time and end_time:
        try:
            from yt_dlp.utils import parse_duration

            start_sec = parse_duration(start_time)
            end_sec = parse_duration(end_time)

            if start_sec is None or end_sec is None:
                raise ValueError("Could not parse time format")
            if start_sec >= end_sec:
                raise ValueError(
                    f"Start time ({start_time}) must be before end time ({end_time})"
                )
            if start_sec < 0 or end_sec < 0:
                raise ValueError(f"Time values must be non-negative")

            ydl_opts["download_ranges"] = lambda info, ydl: [
                {"start_time": start_sec, "end_time": end_sec}
            ]
            ydl_opts["force_keyframes_at_cuts"] = True
        except Exception as e:
            raise ValueError(f"Invalid time range format: {e}") from e

    postprocessors = []

    if add_metadata:
        ydl_opts["addmetadata"] = True
        postprocessors.append({"key": "FFmpegMetadata"})

    if embed_thumbnail:
        ydl_opts["writethumbnail"] = True
        postprocessors.append({"key": "EmbedThumbnail"})

    if recode_video:
        postprocessors.append(
            {"key": "FFmpegVideoConvertor", "preferredformat": recode_video}
        )

    if sponsorblock_remove:
        postprocessors.append(
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
                "when": "after_filter",
            }
        )

    if gpu_accel and gpu_accel.lower() != "none":
        ffmpeg_args = []
        if gpu_accel == "cuda":
            ffmpeg_args.extend(["-c:v", "h264_nvenc", "-preset", "fast"])
        elif gpu_accel == "vulkan":
            ffmpeg_args.extend(["-c:v", "h264_vaapi"])
        if ffmpeg_args:
            ydl_opts["postprocessor_args"] = {"ffmpeg": ffmpeg_args}

    if postprocessors:
        ydl_opts["postprocessors"] = postprocessors

    if proxy:
        proxy = proxy.strip()
        if not proxy.startswith(("http://", "https://", "socks4://", "socks5://")):
            logger.warning(f"Proxy may be invalid: {proxy}")
        ydl_opts["proxy"] = proxy

    if rate_limit:
        rate_limit_clean = rate_limit.strip()
        if rate_limit_clean:
            import re

            # Accept formats like "50K", "4.2M", "1G" and optional "/s" suffix
            if not re.match(
                r"^\d+(\.\d+)?[KMGT]?(?:/s)?$", rate_limit_clean, re.IGNORECASE
            ):
                raise ValueError(f"Invalid rate limit format: {rate_limit}")
            ydl_opts["ratelimit"] = rate_limit_clean

    if cookies_from_browser:
        ydl_opts["cookies_from_browser"] = (
            cookies_from_browser,
            cookies_from_browser_profile if cookies_from_browser_profile else None,
        )

    # Execute Download
    YTDLPWrapper.download(
        url, output_path, progress_hook, download_item, ydl_opts, cancel_token
    )
