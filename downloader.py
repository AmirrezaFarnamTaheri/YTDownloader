import yt_dlp
import os
import logging
from typing import Optional, Dict, List, Any, Callable
from pathlib import Path

# Import the new generic downloader module
from generic_downloader import TelegramExtractor, GenericExtractor, download_generic

logger = logging.getLogger(__name__)


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
            return info
        # If scraping fails, fall through to see if yt-dlp can handle it (unlikely but safe)

    try:
        ydl_opts = {
            "quiet": True,
            "listsubtitles": True,
            "noplaylist": True,
            "socket_timeout": 30,
            # 'extract_flat': True, # Don't extract flat, we need format info
        }

        if cookies_from_browser:
            ydl_opts["cookies_from_browser"] = (
                cookies_from_browser,
                cookies_from_browser_profile if cookies_from_browser_profile else None,
            )

        logger.info(f"Fetching video info for: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)

            # Check if yt-dlp fell back to generic and didn't find much
            # Sometimes generic extractor returns a webpage without video formats
            extractor = info_dict.get("extractor_key", "")
            formats = info_dict.get("formats", [])

            # If generic extractor and no video/audio formats found, it might be a file link
            # that yt-dlp didn't handle well (or handled as "unknown_video")
            if extractor == "Generic" and not formats:
                # Try our generic extractor to be sure
                generic_info = GenericExtractor.extract(url)
                if generic_info:
                    return generic_info

            # Process yt-dlp info
            subtitles: Dict[str, List[str]] = {}

            # Check manual subtitles
            if "subtitles" in info_dict and info_dict["subtitles"]:
                for lang, subs in info_dict["subtitles"].items():
                    if isinstance(subs, list):
                        formats = [
                            sub.get("ext", "vtt") if isinstance(sub, dict) else str(sub)
                            for sub in subs
                        ]
                    else:
                        formats = ["vtt"]
                    if formats:
                        subtitles[lang] = formats
                    else:
                        subtitles[lang] = ["vtt"]

            # Check automatic captions
            if "automatic_captions" in info_dict and info_dict["automatic_captions"]:
                for lang, subs in info_dict["automatic_captions"].items():
                    if isinstance(subs, list):
                        formats = [
                            sub.get("ext", "vtt") if isinstance(sub, dict) else str(sub)
                            for sub in subs
                        ]
                    else:
                        formats = ["vtt"]
                    auto_lang = f"{lang} (Auto)" if lang not in subtitles else lang
                    if formats_list:
                        subtitles[auto_lang] = formats_list
                    else:
                        subtitles[auto_lang] = ["vtt"]

            video_streams: List[Dict[str, Any]] = []
            audio_streams: List[Dict[str, Any]] = []

            formats = info_dict.get("formats", [])

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
        # Fallback to Generic Extractor
        generic_info = GenericExtractor.extract(url)
        if generic_info:
            return generic_info
        return None
    except Exception as e:
        logger.exception(f"Unexpected error while fetching video info: {e}")
        return None


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
    cancel_token: Optional[Any] = None,
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
    # Ensure output path exists
    Path(output_path).mkdir(parents=True, exist_ok=True)

    # Check for hints in download_item or detect
    is_telegram = (download_item or {}).get('is_telegram') or TelegramExtractor.is_telegram_url(url)

    if force_generic:
        logger.info("Force Generic Mode enabled. Bypassing yt-dlp extraction.")
        # Attempt generic extraction immediately
        info = GenericExtractor.extract(url)
        if info and info.get("video_streams"):
            direct_url = info["video_streams"][0]["url"]
            ext = info["video_streams"][0]["ext"]
            title = info["title"]
            filename = f"{title}.{ext}" if not title.endswith(f".{ext}") else title

            logger.info(f"Downloading Generic file (Forced): {filename}")
            download_generic(
                direct_url,
                output_path,
                filename,
                progress_hook,
                download_item,
                cancel_token,
            )
            return
        else:
            # If force generic fails, we might want to fall back or just fail.
            # Let's try yt-dlp as a fallback if force_generic fails, just in case.
            logger.warning("Force Generic failed. Falling back to yt-dlp...")

    # If it's Telegram, we MUST use our custom logic because yt-dlp fails or does nothing useful.
    if is_telegram:
        info = TelegramExtractor.extract(url)
        if info and info.get("video_streams"):
            direct_url = info["video_streams"][0]["url"]
            ext = info["video_streams"][0]["ext"]
            title = info["title"]
            filename = f"{title}.{ext}"

            # Use Generic Downloader for the direct link
            logger.info(f"Downloading Telegram media: {filename}")
            download_generic(
                direct_url,
                output_path,
                filename,
                progress_hook,
                download_item,
                cancel_token,
            )
            return
        else:
            raise Exception("Could not extract Telegram media")

    # For generic files, we could try GenericExtractor if yt-dlp fails.
    # But since we are inside download_video, we usually expect yt-dlp to work unless we specifically identified it as generic.
    # However, if the user put a generic link in Queue, we might not know until we try.

    # Let's try yt-dlp first. If it fails with DownloadError, we check Generic.

    # Build output template with proper escaping
    if output_template:
        outtmpl = os.path.join(output_path, output_template)
    else:
        outtmpl = os.path.join(output_path, "%(title)s.%(ext)s")

    ydl_opts: Dict[str, Any] = {
        "format": video_format,
        "playlist": playlist,
        "outtmpl": outtmpl,
        "progress_hooks": [lambda d: progress_hook(d, download_item)],
        "continuedl": True,
        "retries": 10,
        "fragment_retries": 10,
        "quiet": False,
        "no_warnings": False,
        "noplaylist": not playlist,
    }

    if match_filter:
        ydl_opts["matchtitle"] = match_filter

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
            ydl_opts["download_ranges"] = lambda info, ydl: [
                {"start_time": start_sec, "end_time": end_sec}
            ]
            ydl_opts["force_keyframes_at_cuts"] = True
        except Exception as e:
            raise ValueError(f"Invalid time range format: {e}") from e

    postprocessors = ydl_opts.get("postprocessors", [])

    if add_metadata:
        ydl_opts["addmetadata"] = True
        postprocessors.append({"key": "FFmpegMetadata"})

    if embed_thumbnail:
        ydl_opts["writethumbnail"] = True
        postprocessors.append({"key": "EmbedThumbnail"})

    if recode_video:
        postprocessors.append(
            {"key": "FFmpegVideoConvertor", "preferedformat": recode_video}
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
        ydl_opts["ratelimit"] = rate_limit.strip().upper()

    if cookies_from_browser:
        ydl_opts["cookies_from_browser"] = (
            cookies_from_browser,
            cookies_from_browser_profile if cookies_from_browser_profile else None,
        )

    if cancel_token:
        ydl_opts["progress_hooks"].append(lambda d: cancel_token.check(d))

    try:
        logger.info(f"Starting download: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logger.info(f"Download completed: {url}")

    except yt_dlp.utils.DownloadError as e:
        if "by user" in str(e):
            logger.info(f"Download cancelled by user: {url}")
            return

        # Fallback to Generic Downloader if yt-dlp fails
        logger.warning(f"yt-dlp failed ({e}). Attempting Generic Downloader...")

        info = GenericExtractor.extract(url)
        if info and info.get("video_streams"):
            direct_url = info["video_streams"][0]["url"]
            ext = info["video_streams"][0]["ext"]
            title = info["title"]

            # If title has no extension, add it
            if not title.lower().endswith(f".{ext.lower()}"):
                filename = f"{title}.{ext}"
            else:
                filename = title

            logger.info(f"Downloading Generic file: {filename}")
            download_generic(
                direct_url,
                output_path,
                filename,
                progress_hook,
                download_item,
                cancel_token,
            )
        else:
            logger.error("Generic extraction also failed.")
            raise e

    except Exception as e:
        logger.exception(f"Unexpected error during download: {e}")
        raise
