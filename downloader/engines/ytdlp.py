import logging
import os
from typing import Any, Callable, Dict, Optional, cast

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
        # pylint: disable=unused-argument
        return True

    def download(
        self,
        url: str,
        progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
        download_item: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute download.

        Args:
            url: The URL to download.
            progress_hook: Callback for progress updates.
            cancel_token: Object to check for cancellation.
            download_item: Optional dictionary containing item details (for compatibility).
            output_path: Optional output path override (for compatibility).

        Returns:
            Dict containing metadata of downloaded file.

        Raises:
            Exception: If download fails or is cancelled.
        """
        # pylint: disable=unused-argument
        options = self.options.copy()

        # Handle path override
        if output_path and "outtmpl" in options:
            # Basic replacement if outtmpl starts with old path?
            # Or just assume caller handled options before passing here.
            # Ideally options already has correct path.
            # If output_path is passed, we might need to update outtmpl if it was just a filename template.
            pass

        # Add progress hooks
        hooks = options.setdefault("progress_hooks", [])

        # 1. Cancellation Hook
        def check_cancel(d):
            if cancel_token:
                # Support both method check() and attribute cancelled
                if hasattr(cancel_token, "is_set") and cancel_token.is_set():
                    # pylint: disable=broad-exception-raised
                    raise InterruptedError("Download Cancelled by user")
                if hasattr(cancel_token, "cancelled") and cancel_token.cancelled:
                    # pylint: disable=broad-exception-raised
                    raise InterruptedError("Download Cancelled by user")

        hooks.append(check_cancel)

        # 2. Progress Hook
        if progress_hook:
            hooks.append(progress_hook)

        # 3. Logger redirection (optional, to keep stdout clean)
        # options['logger'] = logger # This might be too verbose

        try:
            logger.info("Starting yt-dlp download: %s", url)
            # mypy: options is dict[str, Any], but YoutubeDL expects _Params | None
            with yt_dlp.YoutubeDL(options) as ydl:  # type: ignore[arg-type]
                # Extract info and download
                info = ydl.extract_info(url, download=True)

                # Handle null info (can happen in some cases)
                if not info:
                    # pylint: disable=broad-exception-raised
                    raise Exception("Failed to extract video info")

                # Handle Playlists
                if "entries" in info:
                    entries_raw = info.get("entries", [])
                    # entries_raw is typed as object by mypy, but we know it is iterable if not None
                    # We cast to Iterable[Any] to satisfy mypy
                    from typing import Iterable

                    entries_iterable = cast(Iterable[Any], entries_raw)
                    entries_list = (
                        list(entries_iterable) if entries_raw is not None else []
                    )
                    return {
                        "filename": info.get("title", "Playlist"),
                        # Omit filepath for playlists to avoid misleading template string
                        "title": info.get("title", "Playlist"),
                        "entries": len(entries_list),
                        "type": "playlist",
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
                    "type": "video",
                }

        except Exception as e:
            # Detect cancellation to re-raise cleanly
            msg = str(e)
            if "Cancelled" in msg or "Interrupted" in msg:
                logger.info("Download cancelled via hook.")
                # pylint: disable=broad-exception-raised
                raise InterruptedError("Download Cancelled by user") from e

            logger.error("yt-dlp error for %s: %s", url, e)
            raise
