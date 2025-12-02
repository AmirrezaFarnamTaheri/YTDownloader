"""
Telegram extractor module.
Supports downloading files from public Telegram channels (t.me/...).
"""

import logging
import os
import re
from typing import Any, Callable, Dict, Optional

import requests
from bs4 import BeautifulSoup

from downloader.engines.generic import GenericDownloader

logger = logging.getLogger(__name__)


class TelegramExtractor:
    """
    Extracts and downloads media from public Telegram links.
    """

    @staticmethod
    def is_telegram_url(url: str) -> bool:
        """Check if the URL is a Telegram URL."""
        return "t.me/" in url

    @staticmethod
    def extract(
        url: str,
        output_path: str,
        progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Extract direct link from Telegram preview page and download.
        """
        logger.info("Extracting Telegram media from: %s", url)

        try:
            # Fetch the preview page
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for video or file link
            # Telegram preview often puts video in <video src="..."> or specialized meta tags
            video_tag = soup.find("video")
            download_url = None

            if video_tag and video_tag.get("src"):
                download_url = video_tag.get("src")
            else:
                # Try finding a generic file link (not always exposed in preview)
                # This is limited to what t.me preview shows.
                pass

            if not download_url:
                # Try OpenGraph video
                og_vid = soup.find("meta", property="og:video")
                if og_vid:
                    download_url = og_vid.get("content")

            if not download_url:
                raise ValueError("Could not find media link in Telegram preview")

            logger.info("Found media URL: %s", download_url)

            # Delegate to GenericDownloader
            return GenericDownloader.download(
                download_url,
                output_path,
                progress_hook,
                cancel_token,
                filename=f"telegram_{os.path.basename(url)}.mp4" # Simple default filename
            )

        except Exception as e:
            logger.error("Telegram extraction failed: %s", e)
            raise
