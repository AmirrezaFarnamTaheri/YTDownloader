"""
Telegram extractor module.
Supports downloading files from public Telegram channels (t.me/...).
"""

import logging
import os
import re
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

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
    def get_metadata(url: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from Telegram preview page.
        Returns None if failed or not found.
        """
        logger.info("Extracting Telegram metadata from: %s", url)
        try:
             # Fetch the preview page
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Extract basic info
            title_tag = soup.find("meta", property="og:title")
            title = title_tag.get("content") if title_tag else os.path.basename(url)

            desc_tag = soup.find("meta", property="og:description")
            description = desc_tag.get("content") if desc_tag else ""

            image_tag = soup.find("meta", property="og:image")
            thumbnail = image_tag.get("content") if image_tag else ""

            # Try to find media URL
            download_url = None
            video_tag = soup.find("video")
            if video_tag and video_tag.get("src"):
                download_url = video_tag.get("src")
            else:
                 og_vid = soup.find("meta", property="og:video")
                 if og_vid:
                     download_url = og_vid.get("content")

            if download_url:
                from urllib.parse import urljoin
                # Normalize protocol-relative and relative paths
                download_url = urljoin(url, download_url)
                return {
                    "title": title,
                    "description": description,
                    "thumbnail": thumbnail,
                    "webpage_url": url,
                    "direct_url": download_url,
                    "extractor": "telegram",
                    "duration": 0 # Unknown
                }
            return None

        except Exception as e:
            logger.warning("Failed to extract Telegram metadata: %s", e)
            return None

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
            metadata = TelegramExtractor.get_metadata(url)
            if not metadata or not metadata.get("direct_url"):
                raise ValueError("Could not find media link in Telegram preview")

            download_url = metadata["direct_url"]
            logger.info("Found media URL: %s", download_url)

            # Sanitize filename
            url_path = urlparse(url).path
            # Get the last part of the path, e.g., '123' from '/channel/123'
            file_id = url_path.strip('/').split('/')[-1]
            # Basic sanitization
            safe_file_id = "".join(c for c in file_id if c.isalnum() or c in ('_','-'))
            filename = f"telegram_{safe_file_id or 'media'}.mp4"

            # Delegate to GenericDownloader
            return GenericDownloader.download(
                download_url,
                output_path,
                progress_hook,
                cancel_token,
                filename=filename
            )

        except Exception as e:
            logger.error("Telegram extraction failed: %s", e)
            raise
