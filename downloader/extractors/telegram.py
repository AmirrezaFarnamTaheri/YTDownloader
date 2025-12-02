import logging
import re
from typing import Any, Dict, Optional, Union

import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class TelegramExtractor:
    """
    Extractor for public Telegram media links (e.g., https://t.me/channel/123).
    Supports extracting video and image content from embed pages.
    """

    # Compile regex for performance
    URL_PATTERN = re.compile(r"(^|[:/])t\.me/|telegram\.me/", re.IGNORECASE)
    BG_IMAGE_PATTERN = re.compile(r"url\('?(.*?)'?\)", re.IGNORECASE)
    TITLE_SANITIZE_PATTERN = re.compile(r'[<>:"/\\|?*]')

    @staticmethod
    def is_telegram_url(url: str) -> bool:
        """Check if URL is a Telegram link."""
        return bool(TelegramExtractor.URL_PATTERN.search(url))

    @staticmethod
    def extract(url: str) -> Optional[Dict[str, Any]]:
        """
        Scrapes a public Telegram link to find the video or image source.
        """
        try:
            # Normalize URL to embed view for easier scraping
            if "?embed=1" not in url and "embed=1" not in url:
                embed_url = f"{url}?embed=1"
            else:
                embed_url = url

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            logger.info("Scraping Telegram URL: %s", embed_url)
            try:
                response = requests.get(embed_url, headers=headers, timeout=15)
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error("Failed to fetch Telegram page: %s", e)
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            media_url: Optional[str] = None
            ext = "mp4"

            # 1. Try Video Tag
            video_tag = soup.find("video")
            if isinstance(video_tag, Tag):
                src = video_tag.get("src")
                if isinstance(src, str):
                    media_url = src
                    ext = "mp4"

            # 2. Try Image Div (if no video)
            if not media_url:
                image_tag = soup.find("div", class_="tgme_widget_message_photo_wrap")
                if isinstance(image_tag, Tag):
                    style = image_tag.get("style", "")
                    if isinstance(style, str):
                        match = TelegramExtractor.BG_IMAGE_PATTERN.search(style)
                        if match:
                            media_url = match.group(1)
                            ext = "jpg"

            # 3. Fallback: Open Graph Metadata
            if not media_url:
                media_url = TelegramExtractor._extract_og_content(soup, "og:video")
                if media_url:
                    ext = "mp4"
                else:
                    media_url = TelegramExtractor._extract_og_content(soup, "og:image")
                    if media_url:
                        ext = "jpg"

            if not media_url:
                logger.warning("No media found on Telegram page: %s", url)
                return None

            # Extract Title
            text_div = soup.find("div", class_="tgme_widget_message_text")
            if isinstance(text_div, Tag):
                # Get raw text
                title_text = text_div.get_text(strip=True)
                # Truncate to 100 chars
                title = title_text[:100] if title_text else ""
            else:
                title = ""

            if not title:
                # Fallback title from URL ID
                parts = url.strip("/").split("/")
                title = f"Telegram_{parts[-1]}" if parts else "Telegram_Media"

            # Sanitize Title
            title = TelegramExtractor.TITLE_SANITIZE_PATTERN.sub("", title)

            # Return structure compatible with GenericDownloader / YTDLPWrapper result
            return {
                "title": title,
                "thumbnail": None, # Could extract if needed
                "duration": None,
                "url": url, # Original URL
                "direct_url": media_url, # Helper for GenericDownloader if needed
                # Structure expected by core if not passing through GenericDownloader directly:
                "video_streams": [
                    {
                        "url": media_url,
                        "format_id": "telegram_source",
                        "ext": ext,
                        "resolution": "Original",
                        "filesize": None,
                    }
                ],
                "audio_streams": [],
                "is_telegram": True,
            }

        except Exception as e:
            logger.error("Telegram extraction error: %s", e, exc_info=True)
            return None

    @staticmethod
    def _extract_og_content(soup: BeautifulSoup, property_name: str) -> Optional[str]:
        """Helper to extract Open Graph meta tags."""
        tag = soup.find("meta", property=property_name)
        if isinstance(tag, Tag):
            content = tag.get("content")
            if isinstance(content, str):
                return content
        return None
