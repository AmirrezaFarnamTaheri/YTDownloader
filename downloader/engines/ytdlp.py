import logging
import os
from typing import Any, Callable, Dict, Optional

import yt_dlp

logger = logging.getLogger(__name__)


class YTDLPWrapper:
    """
    Wrapper around yt-dlp to handle configuration, execution, and error mapping.
    Ensures consistent behavior for cancellation and progress reporting.
    """

    def __init__(self, options: Dict[str, Any]):
        self.options = options.copy()

    @staticmethod
    def supports(url: str) -> bool:
        """
        Check if yt-dlp supports the URL.
        """
        # We generally assume yt-dlp supports most things, or we fail and fallback.
        # However, we can use extractors to check.
        # For now, simplistic check:
        return True

    def download(
        self,
        url: str,
        progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute download.

        Args:
            url: The URL to download.
            progress_hook: Callback for progress updates.
            cancel_token: Object to check for cancellation.

        Returns:
            Dict containing metadata of downloaded file.

        Raises:
            Exception: If download fails or is cancelled.
        """
        options = self.options.copy()

        # Add progress hooks
        hooks = options.setdefault("progress_hooks", [])

        # 1. Cancellation Hook
        def check_cancel(d):
            if cancel_token:
                # Support both method check() and attribute cancelled
                if hasattr(cancel_token, 'is_set') and cancel_token.is_set():
                     raise InterruptedError("Download Cancelled by user")
                if hasattr(cancel_token, 'cancelled') and cancel_token.cancelled:
                    raise InterruptedError("Download Cancelled by user")

        hooks.append(check_cancel)

        # 2. Progress Hook
        if progress_hook:
            hooks.append(progress_hook)

        # 3. Logger redirection (optional, to keep stdout clean)
        # options['logger'] = logger # This might be too verbose

        try:
            logger.info("Starting yt-dlp download: %s", url)
            with yt_dlp.YoutubeDL(options) as ydl:
                # Extract info and download
                info = ydl.extract_info(url, download=True)

                # Handle null info (can happen in some cases)
                if not info:
                    raise Exception("Failed to extract video info")

                # Handle Playlists
                if "entries" in info:
                    # Return summary for playlist
                    # We might want to return the first item's path or the directory?
                    return {
                        "filename": info.get("title", "Playlist"),
                        "filepath": options.get("outtmpl", "."),
                        "title": info.get("title", "Playlist"),
                        "entries": len(list(info["entries"])),
                        "type": "playlist"
                    }

                # Handle Single Video
                filename = ydl.prepare_filename(info)

                # Check if file actually exists (sometimes prepare_filename differs from actual output)
                # But mostly it's correct.

                return {
                    "filename": os.path.basename(filename),
                    "filepath": filename,
                    "title": info.get("title", "Unknown Title"),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader"),
                    "type": "video"
                }

        except Exception as e:
            # Detect cancellation to re-raise cleanly
            msg = str(e)
            if "Cancelled" in msg:
                 logger.info("Download cancelled via hook.")
                 raise InterruptedError("Download Cancelled by user") from e

            logger.error("yt-dlp error for %s: %s", url, e)
            raise
