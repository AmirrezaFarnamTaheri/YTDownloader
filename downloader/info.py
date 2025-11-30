import logging
import os
import signal
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import yt_dlp

from downloader.extractors.generic import GenericExtractor
from downloader.extractors.telegram import TelegramExtractor

logger = logging.getLogger(__name__)


@contextmanager
def extraction_timeout(seconds=30):
    """Context manager for timeout on info extraction."""

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Info extraction timed out after {seconds}s")

    if os.name != "nt":
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        yield  # No timeout on Windows


def get_video_info(
    url: str,
    cookies_from_browser: Optional[str] = None,
    cookies_from_browser_profile: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetches video metadata without downloading the video.
    Tries yt-dlp first, then falls back to Telegram scraping or Generic file check.
    """

    # 1. Check for Telegram URL explicitly first (faster)
    if TelegramExtractor.is_telegram_url(url):
        logger.info("Detected Telegram URL. Attempting to scrape...")
        info = TelegramExtractor.extract(url)
        if info:
            logger.info("Successfully extracted Telegram info.")
            return info
        logger.warning("Telegram extraction failed, falling back to yt-dlp.")
        # If scraping fails, fall through to see if yt-dlp can handle it

    try:
        ydl_opts = {
            "quiet": True,
            "listsubtitles": True,
            "noplaylist": True,
            "socket_timeout": 30,
        }

        if cookies_from_browser:
            logger.debug(f"Using browser cookies from: {cookies_from_browser}")
            ydl_opts["cookies_from_browser"] = (
                cookies_from_browser,
                cookies_from_browser_profile if cookies_from_browser_profile else None,
            )

        logger.info(f"Fetching video info for: {url}")

        # Wrap extraction in timeout
        with extraction_timeout(45):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)

            # Check if yt-dlp fell back to generic and didn't find much
            extractor = info_dict.get("extractor_key", "")
            formats = info_dict.get("formats", [])

            # If generic extractor and no video/audio formats found, it might be a file link
            if extractor == "Generic" and not formats:
                logger.debug("yt-dlp returned Generic extractor with no formats. Trying GenericExtractor fallback.")
                generic_info = GenericExtractor.extract(url)
                if generic_info:
                    return generic_info

            # Process yt-dlp info
            subtitles: Dict[str, List[str]] = {}

            # Check manual subtitles
            if "subtitles" in info_dict and info_dict["subtitles"]:
                for lang, subs in info_dict["subtitles"].items():
                    if isinstance(subs, list):
                        formats_list = [
                            sub.get("ext", "vtt") if isinstance(sub, dict) else str(sub)
                            for sub in subs
                        ]
                    else:
                        formats_list = ["vtt"]
                    if formats_list:
                        subtitles[lang] = formats_list

            # Check automatic captions
            if "automatic_captions" in info_dict and info_dict["automatic_captions"]:
                for lang, subs in info_dict["automatic_captions"].items():
                    if isinstance(subs, list):
                        formats_list = [
                            sub.get("ext", "vtt") if isinstance(sub, dict) else str(sub)
                            for sub in subs
                        ]
                    else:
                        formats_list = ["vtt"]
                    auto_lang = f"{lang} (Auto)" if lang not in subtitles else lang
                    if formats_list:
                        subtitles[auto_lang] = formats_list

            video_streams: List[Dict[str, Any]] = []
            audio_streams: List[Dict[str, Any]] = []

            # If no formats but direct is True (generic file handled by yt-dlp)
            if not formats and info_dict.get("direct"):
                video_streams.append(
                    {
                        "format_id": "direct",
                        "ext": info_dict.get("ext", "unknown"),
                        "resolution": "N/A",
                        "filesize": None,
                        "url": info_dict.get("url"),
                    }
                )
            else:
                for f in formats:
                    if f.get("vcodec") != "none":
                        video_streams.append(
                            {
                                "format_id": f.get("format_id"),
                                "ext": f.get("ext"),
                                "resolution": f.get("resolution"),
                                "fps": f.get("fps"),
                                "vcodec": f.get("vcodec"),
                                "acodec": f.get("acodec"),
                                "filesize": f.get("filesize"),
                            }
                        )
                    elif f.get("vcodec") == "none" and f.get("acodec") != "none":
                        audio_streams.append(
                            {
                                "format_id": f.get("format_id"),
                                "ext": f.get("ext"),
                                "abr": f.get("abr"),
                                "acodec": f.get("acodec"),
                                "filesize": f.get("filesize"),
                            }
                        )

            result = {
                "title": info_dict.get("title", "N/A"),
                "thumbnail": info_dict.get("thumbnail", None),
                "duration": info_dict.get("duration_string", "N/A"),
                "subtitles": subtitles,
                "video_streams": video_streams,
                "audio_streams": audio_streams,
                "chapters": info_dict.get("chapters", None),
                "original_url": url,
            }

            logger.info(f"Successfully fetched video info: {result['title']}")
            return result

    except yt_dlp.utils.DownloadError as e:
        logger.warning(f"yt-dlp failed: {e}. Trying Generic Extractor...")
        generic_info = GenericExtractor.extract(url)
        if generic_info:
            return generic_info
        return None
    except Exception as e:
        logger.error(f"Unexpected error while fetching video info: {e}", exc_info=True)
        return None
