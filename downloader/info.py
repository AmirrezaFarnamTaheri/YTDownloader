"""
Module for fetching video metadata using yt-dlp or fallback extractors.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, List, Optional, Tuple, cast

import yt_dlp

from downloader.extractors.generic import GenericExtractor
from downloader.extractors.telegram import TelegramExtractor

logger = logging.getLogger(__name__)


def _extract_telegram_info(url: str) -> Optional[Dict[str, Any]]:
    """Attempt to scrape Telegram URL."""
    logger.info("Detected Telegram URL. Attempting to scrape...")
    info = TelegramExtractor.get_metadata(url)
    if info:
        return {
            "title": info.get("title", "Unknown"),
            "thumbnail": info.get("thumbnail"),
            "duration": "N/A",
            "subtitles": {},
            "video_streams": [
                {
                    "format_id": "telegram_direct",
                    "ext": "mp4",
                    "resolution": "Unknown",
                    "filesize": None,
                }
            ],
            "audio_streams": [],
            "original_url": url,
        }
    return None


def _extract_generic_info(url: str) -> Optional[Dict[str, Any]]:
    """Attempt GenericExtractor fallback."""
    generic_info = GenericExtractor.get_metadata(url)
    if generic_info:
        return {
            "title": generic_info.get("title"),
            "thumbnail": None,
            "duration": "N/A",
            "subtitles": {},
            "video_streams": [
                {
                    "format_id": "direct",
                    "ext": "unknown",
                    "filesize": generic_info.get("filesize"),
                    "resolution": "N/A",
                }
            ],
            "audio_streams": [],
            "original_url": url,
        }
    return None


def _process_subtitles(info_dict: Dict[str, Any]) -> Dict[str, List[str]]:
    """Process subtitles from yt-dlp info."""
    subtitles: Dict[str, List[str]] = {}

    # Check manual subtitles
    raw_subs = info_dict.get("subtitles")
    if raw_subs and hasattr(raw_subs, "items"):
        for lang, subs in raw_subs.items():
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
    raw_auto = info_dict.get("automatic_captions")
    if raw_auto and hasattr(raw_auto, "items"):
        for lang, subs in raw_auto.items():
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

    return subtitles


def _process_streams(
    info_dict: Dict[str, Any], formats: Optional[List[Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Process video and audio streams from yt-dlp info."""
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
        # Handle possible None for formats
        formats_iter = formats if formats is not None else []
        for f in formats_iter:
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
    return video_streams, audio_streams


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
        return _extract_telegram_info(url)

    try:
        ydl_opts: Dict[str, Any] = {
            "quiet": True,
            "listsubtitles": True,
            "noplaylist": True,
            "socket_timeout": 30,
        }

        if cookies_from_browser:
            logger.debug("Using browser cookies from: %s", cookies_from_browser)
            # Tuple cast for mypy
            cookies_tuple: Tuple[str, Optional[str]] = (
                cookies_from_browser,
                cookies_from_browser_profile,
            )
            ydl_opts["cookies_from_browser"] = cookies_tuple

        logger.info("Fetching video info for: %s", url)

        # Execute extraction with cross-platform timeout
        def _fetch():
            # pylint: disable=line-too-long
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                return cast(Dict[str, Any], ydl.extract_info(url, download=False))

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_fetch)
                info_dict = future.result(timeout=45)
        except FuturesTimeoutError as exc:
            logger.error("Info extraction timed out after 45s")
            raise TimeoutError("Info extraction timed out") from exc

        # Check if yt-dlp fell back to generic and didn't find much
        if info_dict:
            extractor = info_dict.get("extractor_key", "")
            formats = info_dict.get("formats", [])

            # If generic extractor and no video/audio formats found, it might be a file link
            if extractor == "Generic" and not formats:
                # pylint: disable=line-too-long
                logger.debug(
                    "yt-dlp returned Generic extractor with no formats. Trying GenericExtractor fallback."
                )
                generic_info = _extract_generic_info(url)
                if generic_info:
                    return generic_info

            subtitles = _process_subtitles(info_dict)
            video_streams, audio_streams = _process_streams(info_dict, formats)

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

            logger.info("Successfully fetched video info: %s", result["title"])
            return result

    except yt_dlp.utils.DownloadError as e:
        logger.warning("yt-dlp failed: %s. Trying Generic/Telegram fallback.", e)
        # Fallback for when yt-dlp fails (e.g. unknown service)
        return _extract_generic_info(url)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Unexpected error while fetching video info: %s", e, exc_info=True)
        return None
