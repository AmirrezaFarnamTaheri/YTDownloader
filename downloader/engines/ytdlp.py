import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

import yt_dlp

from downloader.engines.generic import download_generic
from downloader.extractors.generic import GenericExtractor

if TYPE_CHECKING:
    from utils import CancelToken

logger = logging.getLogger(__name__)


class YTDLPWrapper:
    @staticmethod
    def download(
        url: str,
        output_path: str,
        progress_hook: Callable,
        download_item: Dict[str, Any],
        options: Dict[str, Any],
        cancel_token: Optional["Any"] = None,
    ) -> None:
        """
        Executes yt-dlp download with provided options.
        Handles fallback to Generic Downloader if yt-dlp fails.
        """

        # Create a shallow copy of options to avoid accumulating hooks in the original dict
        # if it's reused by the caller.
        options = options.copy()

        # Ensure progress_hooks list exists
        hooks = options.setdefault("progress_hooks", [])
        # Also copy the hooks list so we don't modify the original list object
        # if it was shared.
        options["progress_hooks"] = list(hooks)
        hooks = options["progress_hooks"]

        # Add cancel token check to progress hooks (if provided)
        if cancel_token:
            hooks.append(lambda d: cancel_token.check(d))

        # Basic progress hook wrapper for UI updates
        hooks.append(lambda d: progress_hook(d, download_item))

        try:
            logger.info(f"Starting yt-dlp download: {url}")
            logger.debug(f"yt-dlp options keys: {list(options.keys())}")
            with yt_dlp.YoutubeDL(options) as ydl:  # type: ignore
                logger.debug("Executing ydl.download()...")
                ydl.download([url])
            logger.info(f"yt-dlp download completed: {url}")

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

                # Normalize extension handling
                title_lower = title.lower()
                ext_lower = ext.lower()

                # Sanitize title
                from pathlib import Path

                from downloader.core import _sanitize_filename

                safe_title = Path(title).name
                safe_title = _sanitize_filename(safe_title)

                if safe_title != title:
                    logger.warning(
                        f"Sanitized title (Fallback) from '{title}' to '{safe_title}'"
                    )

                if not safe_title.lower().endswith(f".{ext_lower}"):
                    filename = f"{safe_title}.{ext}"
                else:
                    filename = safe_title

                logger.info(f"Downloading Generic file (Fallback): {filename}")
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
            logger.exception(f"Unexpected error during yt-dlp download: {e}")
            raise
