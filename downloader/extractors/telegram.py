# pylint: disable=line-too-long,too-many-locals,too-many-branches
"""
Telegram extractor module.
Extracts metadata and media URLs from public Telegram posts (t.me/...).
"""

import logging
import re
from typing import Any, Callable, Dict, Optional, Union
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from downloader.utils.constants import RESERVED_FILENAMES
from ui_utils import validate_url

logger = logging.getLogger(__name__)


class TelegramExtractor:
    """
    Extracts media from public Telegram links.
    """

    @staticmethod
    def is_telegram_url(url: str) -> bool:
        """Check if URL is a supported Telegram link."""
        return "t.me/" in url and validate_url(url)

    @staticmethod
    def get_metadata(url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape the public Telegram page to find the media URL and metadata.
        Returns a dict with 'url', 'title', 'thumbnail' or None.
        Safely limits memory usage by streaming the response.
        """
        try:
            # We need to impersonate a browser to get the preview page
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            # Use stream=True to prevent loading large responses into memory
            with requests.get(
                url, headers=headers, timeout=10, stream=True
            ) as response:
                response.raise_for_status()

                # Limit response reading to 2MB to prevent DoS via large HTML/files
                max_bytes = 2 * 1024 * 1024
                content = b""
                for chunk in response.iter_content(chunk_size=8192):
                    content += chunk
                    if len(content) > max_bytes:
                        logger.warning("Telegram response too large, aborting.")
                        return None

            soup = BeautifulSoup(content, "html.parser")

            # Extract Title/Description
            title: Union[str, None] = "Telegram Video"
            title_tag = soup.find("meta", property="og:description")

            if isinstance(title_tag, Tag):
                content_attr = title_tag.get("content")
                if isinstance(content_attr, str):
                    title = content_attr
                elif isinstance(content_attr, list):
                    title = str(content_attr[0])

            # Extract Video URL
            video_url = None
            video_tag = soup.find("video")

            if isinstance(video_tag, Tag):
                src = video_tag.get("src")
                if isinstance(src, str):
                    video_url = src

            # If no video tag, check for og:video
            if not video_url:
                og_vid = soup.find("meta", property="og:video")
                if isinstance(og_vid, Tag):
                    content_attr = og_vid.get("content")
                    if isinstance(content_attr, str):
                        video_url = content_attr

            # Validate extracted URL
            if video_url and not video_url.startswith("http"):
                # Handle relative URLs if any (unlikely for og tags but possible in src)
                video_url = urljoin(url, video_url)
                logger.debug("Resolved relative Telegram URL to %s", video_url)

            if not video_url:
                logger.warning("No video found in Telegram link: %s", url)
                return None

            # Extract Thumbnail
            thumbnail = None
            og_image = soup.find("meta", property="og:image")
            if isinstance(og_image, Tag):
                content_attr = og_image.get("content")
                if isinstance(content_attr, str):
                    thumbnail = content_attr

            return {
                "url": video_url,
                "title": str(title)[:100],  # Truncate title
                "thumbnail": str(thumbnail) if thumbnail else None,
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Telegram extraction failed: %s", e)
            return None

    @staticmethod
    def extract(
        url: str,
        output_path: str,
        progress_hook: Optional[Callable] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Download the video from a Telegram link.
        """
        meta = TelegramExtractor.get_metadata(url)
        if not meta or not meta.get("url"):
            raise ValueError("Could not extract video from Telegram link")

        video_url = meta["url"]
        title = meta["title"]

        # Sanitize filename
        filename = re.sub(r"[^A-Za-z0-9\-\_\.]", "", title).strip()
        if not filename:
            filename = "telegram_video"
        if not filename.endswith(".mp4"):
            filename += ".mp4"

        # Reserved names check
        name_root = filename.split(".")[0].upper()
        if name_root in RESERVED_FILENAMES:
            filename = f"_{filename}"

        # Use GenericDownloader to handle the actual file download
        # Avoid circular imports if possible, but GenericDownloader is in engines.
        # pylint: disable=import-outside-toplevel
        from downloader.engines.generic import GenericDownloader

        return GenericDownloader.download(
            video_url,
            output_path,
            progress_hook,
            cancel_token,
            filename=filename,
        )
