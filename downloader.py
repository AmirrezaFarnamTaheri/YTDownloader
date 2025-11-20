import yt_dlp
import os
import logging
from typing import Optional, Dict, List, Any, Callable
from pathlib import Path

logger = logging.getLogger(__name__)

def get_video_info(
    url: str,
    cookies_from_browser: Optional[str] = None,
    cookies_from_browser_profile: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetches video metadata without downloading the video.

    Args:
        url: The URL of the video (YouTube, etc.)
        cookies_from_browser: The name of the browser to load cookies from.
        cookies_from_browser_profile: The name of the browser profile to load cookies from.

    Returns:
        A dictionary containing:
        - title: Video title
        - thumbnail: Thumbnail URL
        - duration: Duration as string
        - subtitles: Dict mapping language codes to available formats
        - video_streams: List of available video formats
        - audio_streams: List of available audio formats
        - chapters: List of chapter information (if available)

    Raises:
        yt_dlp.utils.DownloadError: If video info cannot be fetched

    Returns None if extraction fails.
    """
    try:
        ydl_opts = {
            'quiet': True,
            'listsubtitles': True,
            'noplaylist': True,
            'socket_timeout': 30,
        }

        if cookies_from_browser:
            ydl_opts['cookies_from_browser'] = (
                cookies_from_browser,
                cookies_from_browser_profile if cookies_from_browser_profile else None
            )

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Fetching video info for: {url}")
            info_dict = ydl.extract_info(url, download=False)

            # Extract subtitle information (check both subtitles and automatic_captions)
            subtitles: Dict[str, List[str]] = {}
            
            # Check manual subtitles
            if 'subtitles' in info_dict and info_dict['subtitles']:
                for lang, subs in info_dict['subtitles'].items():
                    if isinstance(subs, list):
                        formats = [sub.get('ext', 'vtt') if isinstance(sub, dict) else str(sub) for sub in subs]
                    else:
                        formats = ['vtt']  # Default format if structure is unexpected
                    if formats:
                        subtitles[lang] = formats
                    else:
                        subtitles[lang] = ['vtt']  # Default format
                logger.debug(f"Found manual subtitles for languages: {list(subtitles.keys())}")
            
            # Check automatic captions (often more available)
            if 'automatic_captions' in info_dict and info_dict['automatic_captions']:
                for lang, subs in info_dict['automatic_captions'].items():
                    if isinstance(subs, list):
                        formats = [sub.get('ext', 'vtt') if isinstance(sub, dict) else str(sub) for sub in subs]
                    else:
                        formats = ['vtt']
                    # Add ' (Auto)' suffix to distinguish from manual
                    auto_lang = f"{lang} (Auto)" if lang not in subtitles else lang
                    if formats:
                        subtitles[auto_lang] = formats
                    else:
                        subtitles[auto_lang] = ['vtt']
                logger.debug(f"Found automatic captions for languages: {list(info_dict['automatic_captions'].keys())}")
            
            if subtitles:
                logger.info(f"Total subtitle languages available: {list(subtitles.keys())}")
            else:
                logger.warning("No subtitles or captions found for this video")

            # Extract video and audio stream information
            formats = info_dict.get('formats', [])
            video_streams: List[Dict[str, Any]] = []
            audio_streams: List[Dict[str, Any]] = []

            for f in formats:
                # A video stream has a video codec
                if f.get('vcodec') != 'none':
                    video_streams.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'resolution': f.get('resolution'),
                        'fps': f.get('fps'),
                        'vcodec': f.get('vcodec'),
                        'acodec': f.get('acodec'),
                        'filesize': f.get('filesize'),
                    })
                elif f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    audio_streams.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'abr': f.get('abr'),
                        'acodec': f.get('acodec'),
                        'filesize': f.get('filesize'),
                    })

            logger.debug(f"Found {len(video_streams)} video and {len(audio_streams)} audio streams")

            result = {
                'title': info_dict.get('title', 'N/A'),
                'thumbnail': info_dict.get('thumbnail', None),
                'duration': info_dict.get('duration_string', 'N/A'),
                'subtitles': subtitles,
                'video_streams': video_streams,
                'audio_streams': audio_streams,
                'chapters': info_dict.get('chapters', None),
            }

            logger.info(f"Successfully fetched video info: {result['title']}")
            return result

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download error while fetching video info: {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error while fetching video info: {e}")
        return None

def download_video(
    url: str,
    progress_hook: Callable,
    download_item: Dict[str, Any],
    playlist: bool = False,
    video_format: str = 'best',
    output_path: str = '.',
    subtitle_lang: Optional[str] = None,
    subtitle_format: str = 'srt',
    split_chapters: bool = False,
    proxy: Optional[str] = None,
    rate_limit: Optional[str] = None,
    cancel_token: Optional[Any] = None,
    cookies_from_browser: Optional[str] = None,
    cookies_from_browser_profile: Optional[str] = None,
    download_sections: Optional[str] = None,
    add_metadata: bool = False,
    embed_thumbnail: bool = False,
    recode_video: Optional[str] = None
) -> None:
    """
    Downloads a video or playlist from the given URL using yt-dlp.

    Args:
        url: The URL of the video or playlist.
        progress_hook: Callback function for progress updates. Called with (status_dict, download_item).
        download_item: Dictionary representing the download item (for passing to progress_hook).
        playlist: Whether to download a playlist (default: False).
        video_format: The format ID or specification to download (default: 'best').
        output_path: The directory to save downloaded files (default: current directory).
        subtitle_lang: The language code of subtitles to download (default: None = no subtitles).
        subtitle_format: Format for subtitles: 'srt', 'vtt', or 'ass' (default: 'srt').
        split_chapters: Whether to split videos into chapters (default: False).
        proxy: Proxy URL for the download (e.g., 'http://proxy:8080') (default: None).
        rate_limit: Download speed limit (e.g., '50K', '4.2M') (default: None).
        cancel_token: CancelToken object for cancellation support (default: None).

    Raises:
        yt_dlp.utils.DownloadError: If download fails (except for user cancellation).
        Exception: Any other unexpected errors during download.
    """
    # Ensure output path exists
    Path(output_path).mkdir(parents=True, exist_ok=True)

    # Sanitize output path to prevent issues
    try:
        output_path = str(Path(output_path).resolve())
    except (OSError, ValueError) as e:
        logger.error(f"Invalid output path: {output_path}, error: {e}")
        raise ValueError(f"Invalid output path: {output_path}") from e
    
    # Build output template with proper escaping
    outtmpl = os.path.join(output_path, '%(title)s.%(ext)s')
    
    ydl_opts: Dict[str, Any] = {
        'format': video_format,
        'playlist': playlist,
        'outtmpl': outtmpl,
        'progress_hooks': [lambda d: progress_hook(d, download_item)],
        'continuedl': True,
        'retries': 10,
        'fragment_retries': 10,
        'quiet': False,
        'no_warnings': False,
        'noplaylist': not playlist,  # Explicitly set playlist behavior
    }

    # Add subtitle options if requested
    if subtitle_lang:
        ydl_opts.update({
            'writesubtitles': True,
            'subtitleslangs': [subtitle_lang],
            'subtitlesformat': subtitle_format,
        })

    # Configure chapter splitting
    if split_chapters:
        ydl_opts['split_chapters'] = True
        ydl_opts['outtmpl'] = os.path.join(
            output_path,
            '%(title)s',
            '%(section_number)02d - %(section_title)s.%(ext)s'
        )

    # Download sections (time range)
    if download_sections:
        # format expected by yt-dlp: "*start-end"
        ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(None, [(None, None)], sections=[download_sections])
        # Force external downloader for accurate cutting if needed (often ffmpeg)
        ydl_opts['force_keyframes_at_cuts'] = True

    # Post-processing options
    postprocessors = ydl_opts.get('postprocessors', [])

    if add_metadata:
        ydl_opts['addmetadata'] = True
        postprocessors.append({'key': 'FFmpegMetadata'})

    if embed_thumbnail:
        ydl_opts['writethumbnail'] = True
        postprocessors.append({'key': 'EmbedThumbnail'})

    if recode_video:
        postprocessors.append({
            'key': 'FFmpegVideoConvertor',
            'preferedformat': recode_video,
        })

    if postprocessors:
        ydl_opts['postprocessors'] = postprocessors

    # Configure proxy if provided (with validation)
    if proxy:
        proxy = proxy.strip()
        if not proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            logger.warning(f"Proxy may be invalid (missing protocol): {proxy}")
        ydl_opts['proxy'] = proxy

    # Configure rate limiting if provided (with validation)
    if rate_limit:
        rate_limit = rate_limit.strip().upper()
        # Validate rate limit format
        import re
        if not re.match(r'^\d+(\.\d+)?[KMGT]?$', rate_limit):
            logger.warning(f"Rate limit format may be invalid: {rate_limit}")
        ydl_opts['ratelimit'] = rate_limit

    if cookies_from_browser:
        ydl_opts['cookies_from_browser'] = (
            cookies_from_browser,
            cookies_from_browser_profile if cookies_from_browser_profile else None
        )

    # Add cancellation support
    if cancel_token:
        ydl_opts['progress_hooks'].append(lambda d: cancel_token.check(d))

    try:
        logger.info(f"Starting download: {url} (format: {video_format}, playlist: {playlist})")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logger.info(f"Download completed: {url}")
    except yt_dlp.utils.DownloadError as e:
        if "by user" in str(e):
            logger.info(f"Download cancelled by user: {url}")
            return  # Download was cancelled by user
        logger.error(f"Download error: {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during download: {e}")
        raise
