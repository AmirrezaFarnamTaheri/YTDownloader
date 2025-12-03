"""
Telegram extractor module.
Supports downloading files from public Telegram channels (t.me/...).
"""

import logging
import os
import re
from typing import Any, Callable, Dict, Optional, cast
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

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
            with requests.get(
                url, headers=headers, timeout=15, stream=True
            ) as response:
                response.raise_for_status()
                # Cap preview payload to 2 MB to prevent excessive memory usage
                max_bytes = 2 * 1024 * 1024
                content = bytearray()
                for chunk in response.iter_content(chunk_size=16384):
                    if not chunk:
                        continue
                    content.extend(chunk)
                    if len(content) > max_bytes:
                        break
                soup = BeautifulSoup(bytes(content), "html.parser")

            # Extract basic info
            title_tag = soup.find("meta", property="og:title")
            # Ensure attributes are strings or handle list if it can be a list (BeautifulSoup specifics)
            title = (
                title_tag.get("content")
                if isinstance(title_tag, Tag)
                and isinstance(title_tag.get("content"), str)
                else os.path.basename(url)
            )

            desc_tag = soup.find("meta", property="og:description")
            description = (
                desc_tag.get("content")
                if isinstance(desc_tag, Tag)
                and isinstance(desc_tag.get("content"), str)
                else ""
            )

            image_tag = soup.find("meta", property="og:image")
            thumbnail = (
                image_tag.get("content")
                if isinstance(image_tag, Tag)
                and isinstance(image_tag.get("content"), str)
                else ""
            )

            # Try to find media URL
            download_url: Optional[str] = None
            video_tag = soup.find("video")
            if (
                isinstance(video_tag, Tag)
                and video_tag.get("src")
                and isinstance(video_tag.get("src"), str)
            ):
                download_url = cast(str, video_tag.get("src"))
            else:
                og_vid = soup.find("meta", property="og:video")
                if (
                    isinstance(og_vid, Tag)
                    and og_vid.get("content")
                    and isinstance(og_vid.get("content"), str)
                ):
                    download_url = cast(str, og_vid.get("content"))

            if download_url:
                # Normalize whitespace
                download_url = (download_url or "").strip()
                # Ensure base URL ends with a slash to correctly resolve relative paths
                base = url if url.endswith("/") else url + "/"
                # Handle protocol-relative URLs explicitly
                if download_url.startswith("//"):
                    download_url = "https:" + download_url
                else:
                    # Normalize relative paths against the page URL
                    download_url = urljoin(base, download_url)

                # Validate final scheme to avoid javascript:, data:, etc.
                parsed = urlparse(download_url)
                if parsed.scheme not in ("http", "https"):
                    download_url = None

                if download_url:
                    return {
                        "title": title,
                        "description": description,
                        "thumbnail": thumbnail,
                        "webpage_url": url,
                        "direct_url": download_url,
                        "extractor": "telegram",
                        "duration": 0,  # Unknown
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

            # Sanitize filename robustly
            url_path = urlparse(url).path
            # Get the last part of the path, e.g., '123' from '/channel/123'
            file_id = url_path.strip("/").split("/")[-1]
            # Remove control chars and invalid filesystem chars
            invalid_chars = r'<>:"/\\|?*' + "".join(map(chr, range(32)))
            safe_file_id = "".join(
                c for c in (file_id or "") if c.isalnum() or c in ("_", "-")
            )
            safe_file_id = "".join(
                c for c in safe_file_id if c not in invalid_chars
            ).strip()
            # Neutralize traversal-like names and problematic leading/trailing dots/spaces
            if safe_file_id in {".", ".."}:
                safe_file_id = "media"
            safe_file_id = safe_file_id.strip(" .")
            while ".." in safe_file_id:
                safe_file_id = safe_file_id.replace("..", "-")
            # Avoid Windows reserved device names
            reserved = {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                "COM1",
                "COM2",
                "COM3",
                "COM4",
                "COM5",
                "COM6",
                "COM7",
                "COM8",
                "COM9",
                "LPT1",
                "LPT2",
                "LPT3",
                "LPT4",
                "LPT5",
                "LPT6",
                "LPT7",
                "LPT8",
                "LPT9",
            }
            if (safe_file_id.split(".")[0].upper() or "") in reserved:
                safe_file_id = f"_{safe_file_id}" if safe_file_id else "media"
            filename = f"telegram_{safe_file_id or 'media'}.mp4"

            # Delegate to GenericDownloader
            return GenericDownloader.download(
                download_url,
                output_path,
                progress_hook,
                cancel_token,
                filename=filename,
            )

        except Exception as e:
            logger.error("Telegram extraction failed: %s", e)
            raise
