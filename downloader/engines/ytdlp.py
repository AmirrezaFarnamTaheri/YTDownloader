import yt_dlp
import os
import logging
from typing import Dict, Any, Callable, Optional, TYPE_CHECKING
from pathlib import Path
from downloader.extractors.generic import GenericExtractor
from downloader.engines.generic import download_generic

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

        # Ensure progress_hooks list exists once
        hooks = options.setdefault("progress_hooks", [])

        # Add cancel token check to progress hooks (if provided)
        if cancel_token:
            hooks.append(lambda d: cancel_token.check(d))

        # Basic progress hook wrapper for UI updates
        hooks.append(lambda d: progress_hook(d, download_item))

        try:
            logger.info(f"Starting yt-dlp download: {url}")
            with yt_dlp.YoutubeDL(options) as ydl:
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

                # If title has no extension, add it
                if not title.lower().endswith(f".{ext.lower()}"):
                    filename = f"{title}.{ext}"
                else:
                    filename = title

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
