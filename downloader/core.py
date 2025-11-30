import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict
from typing import Optional
from typing import Optional as _OptionalStr

from downloader.engines.generic import download_generic
from downloader.engines.ytdlp import YTDLPWrapper
from downloader.extractors.generic import GenericExtractor
from downloader.extractors.telegram import TelegramExtractor
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


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for cross-platform compatibility.
    Replaces illegal characters with underscores.
    """
    # Windows illegal characters: < > : " / \ | ? *
    # Also removing control characters
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)


def _sanitize_template(
    template: _OptionalStr[str], output_path: str = "."
) -> _OptionalStr[str]:
    """
    Robust validation for the output template to prevent path traversal.

    Args:
        template: Output template from user
        output_path: Base output directory

    Returns:
        Sanitized template

    Raises:
        ValueError: If template contains path traversal or absolute paths
    """
    if not template:
        return template

    # Check for path traversal
    if ".." in template.replace("\\", "/"):
        logger.error(f"Path traversal attempt in template: {template}")
        raise ValueError("Output template must not contain '..' segments")

    # Check for absolute paths
    import os

    if os.path.isabs(template):
        logger.error(f"Absolute path attempt in template: {template}")
        raise ValueError("Output template must not be an absolute path")

    # Check for leading slashes
    if template.startswith("/") or template.startswith("\\"):
        raise ValueError("Output template must not start with path separator")

    # Verify the final path would be within output_path
    test_path = os.path.abspath(
        os.path.join(output_path, template.replace("%(title)s", "test"))
    )
    if not test_path.startswith(os.path.abspath(output_path)):
        logger.error(f"Path escape attempt in template: {template}")
        raise ValueError("Output template would escape output directory")

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
    if not os.path.exists(output_path):
        logger.debug(f"Creating output directory: {output_path}")
        os.makedirs(output_path, exist_ok=True)

    # Check for hints in download_item or detect
    is_telegram = (download_item or {}).get(
        "is_telegram"
    ) or TelegramExtractor.is_telegram_url(url)

    logger.info(f"Initiating download_video for URL: {url}")
    logger.debug(
        f"Download Configuration:\n"
        f"  - Output Path: {output_path}\n"
        f"  - Format: {video_format}\n"
        f"  - Playlist: {playlist}\n"
        f"  - Aria2c: {use_aria2c}\n"
        f"  - GPU Accel: {gpu_accel}\n"
        f"  - Force Generic: {force_generic}\n"
        f"  - Is Telegram: {is_telegram}\n"
        f"  - SponsorBlock: {sponsorblock_remove}\n"
        f"  - Time Range: {start_time} - {end_time}\n"
        f"  - Proxy: {'Yes' if proxy else 'No'}"
    )

    if force_generic:
        logger.info("Force Generic Mode enabled. Bypassing yt-dlp extraction.")
        info = GenericExtractor.extract(url)
        if info and info.get("video_streams"):
            direct_url = info["video_streams"][0]["url"]
            ext = info["video_streams"][0]["ext"]
            title = info["title"]

            # Sanitize title to prevent path traversal and Windows issues
            safe_title = Path(title).name
            safe_title = _sanitize_filename(safe_title)

            if safe_title != title:
                logger.warning(f"Sanitized title from '{title}' to '{safe_title}'")

            # Be case-insensitive when checking for existing extension
            if not safe_title.lower().endswith(f".{ext.lower()}"):
                filename = f"{safe_title}.{ext}"
            else:
                filename = safe_title

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
        logger.debug(f"Telegram URL detected, attempting extraction: {url}")
        info = TelegramExtractor.extract(url)
        if info and info.get("video_streams"):
            direct_url = info["video_streams"][0]["url"]
            ext = info["video_streams"][0]["ext"]
            title = info["title"]

            # Sanitize title
            safe_title = Path(title).name
            safe_title = _sanitize_filename(safe_title)
            filename = f"{safe_title}.{ext}"

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

        error_msg = "Could not extract Telegram media"
        logger.error(error_msg)
        raise Exception(error_msg)

    # Build yt-dlp Options
    logger.debug(f"Building yt-dlp options for: {url}")
    if output_template:
        logger.debug(f"Sanitizing user template: {output_template}")
        tmpl = _sanitize_template(output_template)
        if tmpl:
            outtmpl = os.path.join(output_path, tmpl)
        else:
             outtmpl = os.path.join(output_path, "%(title)s.%(ext)s")
    else:
        # We don't sanitize %(title)s here because yt-dlp handles it,
        # but we do want to ensure we don't accidentally introduce paths.
        outtmpl = os.path.join(output_path, "%(title)s.%(ext)s")

    logger.debug(f"Constructed base outtmpl: {outtmpl}")

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
        logger.debug("Enabling aria2c external downloader")
        ydl_opts["external_downloader"] = "aria2c"
        ydl_opts["external_downloader_args"] = ["-x", "16", "-s", "16", "-k", "1M"]

    if subtitle_lang:
        logger.debug(f"Enabling subtitles for language: {subtitle_lang}")
        ydl_opts.update(
            {
                "writesubtitles": True,
                "subtitleslangs": [subtitle_lang],
                "subtitlesformat": subtitle_format,
            }  # type: ignore
        )

    if split_chapters:
        logger.debug("Enabling split chapters")
        ydl_opts["split_chapters"] = True
        ydl_opts["outtmpl"] = os.path.join(
            output_path, "%(title)s", "%(section_number)02d - %(section_title)s.%(ext)s"
        )

    if start_time and end_time:
        logger.debug(f"Configuring download range: {start_time} to {end_time}")
        try:
            from yt_dlp.utils import parse_duration

            start_sec = parse_duration(start_time)
            end_sec = parse_duration(end_time)

            if start_sec is None or end_sec is None:
                raise ValueError("Could not parse time format")

            # Validate parsed times
            if start_sec >= end_sec:
                raise ValueError(
                    f"Start time ({start_time}) must be before end time ({end_time})"
                )
            if start_sec < 0 or end_sec < 0:
                raise ValueError(f"Time values must be non-negative")

            # Sanity check: end time shouldn't be absurdly long
            max_duration = 24 * 3600  # 24 hours
            if end_sec > max_duration:
                logger.warning(
                    f"End time {end_sec}s seems very long (>{max_duration/3600}h)"
                )

            ydl_opts["download_ranges"] = lambda info, ydl: [
                {"start_time": start_sec, "end_time": end_sec}
            ]
            ydl_opts["force_keyframes_at_cuts"] = True
        except Exception as e:
            logger.error(f"Failed to configure time range: {e}", exc_info=True)
            raise ValueError(f"Invalid time range format: {e}") from e

    postprocessors = []

    if add_metadata:
        logger.debug("Adding metadata postprocessor")
        ydl_opts["addmetadata"] = True
        postprocessors.append({"key": "FFmpegMetadata"})

    if embed_thumbnail:
        logger.debug("Adding thumbnail embed postprocessor")
        ydl_opts["writethumbnail"] = True
        postprocessors.append({"key": "EmbedThumbnail"})

    if recode_video:
        logger.debug(f"Adding video recode postprocessor: {recode_video}")
        postprocessors.append(
            {"key": "FFmpegVideoConvertor", "preferredformat": recode_video}
        )

    if sponsorblock_remove:
        logger.debug("Adding SponsorBlock postprocessor")
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
        logger.debug(f"Configuring GPU acceleration: {gpu_accel}")
        ffmpeg_args = []
        if gpu_accel == "cuda":
            ffmpeg_args.extend(["-c:v", "h264_nvenc", "-preset", "fast"])
        elif gpu_accel == "vulkan":
            ffmpeg_args.extend(["-c:v", "h264_vaapi"])
        if ffmpeg_args:
            ydl_opts["postprocessor_args"] = {"ffmpeg": ffmpeg_args}

    if postprocessors:
        logger.debug(f"Attached {len(postprocessors)} postprocessors")
        ydl_opts["postprocessors"] = postprocessors

    if proxy:
        proxy = proxy.strip()

        # Strict proxy validation to prevent command injection
        import re

        # Valid proxy format: scheme://[user:pass@]host:port
        proxy_pattern = r"^(https?|socks[45])://([^:@]+:[^:@]+@)?[\w\.\-]+:\d+$"

        if not re.match(proxy_pattern, proxy, re.IGNORECASE):
            logger.error(f"Invalid proxy format: {proxy}")
            raise ValueError(
                f"Invalid proxy format: {proxy}. "
                "Expected: scheme://[user:pass@]host:port "
                "(e.g., http://proxy.example.com:8080)"
            )

        # Check for command injection attempts
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]
        for char in dangerous_chars:
            if char in proxy:
                logger.error(f"Dangerous character '{char}' in proxy string")
                raise ValueError(f"Dangerous character '{char}' not allowed in proxy")

        # Extract and validate port
        port = proxy.split(":")[-1]
        try:
            port_num = int(port)
            if not (1 <= port_num <= 65535):
                logger.error(f"Invalid port number: {port_num}")
                raise ValueError(f"Invalid port number: {port_num}")
        except ValueError:
            logger.error(f"Invalid port in proxy: {port}")
            raise ValueError(f"Invalid port in proxy: {port}")

        ydl_opts["proxy"] = proxy

    if rate_limit:
        rate_limit_clean = rate_limit.strip()
        if rate_limit_clean:
            import re

            # Accept formats like "50K", "4.2M", "1G" and optional "/s" suffix
            if not re.match(
                r"^\d+(\.\d+)?[KMGT]?(?:/s)?$", rate_limit_clean, re.IGNORECASE
            ):
                logger.error(f"Invalid rate limit format: {rate_limit}")
                raise ValueError(f"Invalid rate limit format: {rate_limit}")
            ydl_opts["ratelimit"] = rate_limit_clean

    if cookies_from_browser:
        logger.debug(f"Using cookies from browser: {cookies_from_browser}")
        ydl_opts["cookies_from_browser"] = (
            cookies_from_browser,
            cookies_from_browser_profile if cookies_from_browser_profile else None,
        )

    # Execute Download
    logger.info(f"Delegating download to YTDLPWrapper for {url}")
    logger.debug(f"Final ytdlp options: {ydl_opts}")
    YTDLPWrapper.download(
        url, output_path, progress_hook, download_item, ydl_opts, cancel_token
    )
