import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

import yt_dlp

from downloader.extractors.generic import GenericExtractor

if TYPE_CHECKING:
    from utils import CancelToken

logger = logging.getLogger(__name__)


class YTDLPWrapper:
    """Wrapper around yt-dlp to handle configuration and execution."""

    def __init__(self, options: Dict[str, Any]):
        self.options = options.copy()

    @staticmethod
    def supports(url: str) -> bool:
        """Check if yt-dlp supports the URL."""
        # Simple check, or use yt-dlp's extractor list
        # For now, assume yes unless it's a known unsupported type (e.g. some direct files)
        # But core logic handles generic fallback if yt-dlp fails.
        # We can just return True and let it fail/fallback.
        return True

    def download(
        self,
        url: str,
        progress_hook: Optional[Callable] = None,
        cancel_token: Optional[Any] = None,
        output_path: Optional[str] = None,
        download_item: Optional[Dict[str, Any]] = None,
        options_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute download.

        Returns:
            Dict containing metadata of downloaded file.
        """
        options = self.options.copy()

        if options_override:
            options.update(options_override)
        if output_path:
            options["outtmpl"] = output_path

        # Prepare hooks
        hooks = options.setdefault("progress_hooks", [])

        if cancel_token:
            # yt-dlp progress hook receives a dict 'd'
            def check_cancel(d):
                if cancel_token and hasattr(cancel_token, 'check'):
                    cancel_token.check()
                elif cancel_token and getattr(cancel_token, 'cancelled', False):
                    raise Exception("Cancelled")
            hooks.append(check_cancel)

        if progress_hook:
            hooks.append(progress_hook)

        options["progress_hooks"] = hooks

        try:
            logger.info(f"Starting yt-dlp download: {url}")
            with yt_dlp.YoutubeDL(options) as ydl:
                # Extract info and download
                info = ydl.extract_info(url, download=True)

                # If playlist, info['entries'] exists.
                # If single video, info is the video info.

                if "entries" in info:
                    # It's a playlist. Return summary or first item?
                    # Core expects a dict.
                    return {
                        "filename": "Playlist", # Placeholder
                        "filepath": options.get("outtmpl", "."), # Approximation
                        "title": info.get("title", "Playlist"),
                        "entries": len(info["entries"])
                    }

                # Single video
                filename = ydl.prepare_filename(info)
                return {
                    "filename": info.get("title", "Video"),
                    "filepath": filename,
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader"),
                }

        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            raise
