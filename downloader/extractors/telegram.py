import logging
import re
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class TelegramExtractor:
    @staticmethod
    def is_telegram_url(url: str) -> bool:
        """Check if URL is a Telegram link with proper domain matching."""
        # Match exact domains to avoid false positives like "at.me/" or "not.me/"
        pattern = r'(^|[:/])t\.me/|telegram\.me/'
        return bool(re.search(pattern, url.lower()))

    @staticmethod
    def extract(url: str) -> Optional[Dict[str, Any]]:
        """
        Scrapes a public Telegram link (e.g., https://t.me/channel/123)
        to find the video or image source.
        """
        try:
            # Normalize URL
            if "?embed=1" not in url and "embed=1" not in url:
                embed_url = f"{url}?embed=1"
            else:
                embed_url = url

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            logger.info(f"Scraping Telegram URL: {embed_url}")
            response = requests.get(embed_url, headers=headers, timeout=15)
            if response.status_code != 200:
                logger.error(f"Failed to fetch Telegram page: {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Try to find video
            video_tag = soup.find("video")
            image_tag = soup.find("div", class_="tgme_widget_message_photo_wrap")

            media_url = None
            ext = "mp4"
            is_video = False

            if video_tag:
                src = video_tag.get("src")
                if src:
                    media_url = src
                    is_video = True
                    ext = "mp4"

            if not media_url and image_tag:
                # Extract background-image url
                style = image_tag.get("style", "")
                # style="background-image:url('https://...')"
                match = re.search(r"url\('?(.*?)'?\)", style)
                if match:
                    media_url = match.group(1)
                    is_video = False
                    ext = "jpg"

            if not media_url:
                # Fallback: Check Open Graph tags
                og_video = soup.find("meta", property="og:video")
                if og_video:
                    media_url = og_video.get("content")
                    is_video = True
                else:
                    og_image = soup.find("meta", property="og:image")
                    if og_image:
                        media_url = og_image.get("content")
                        is_video = False
                        ext = "jpg"

            if not media_url:
                logger.warning("No media found on Telegram page.")
                return None

            # Get Title / Text
            text_div = soup.find("div", class_="tgme_widget_message_text")
            title = text_div.get_text(strip=True)[:50] if text_div else "Telegram_Media"
            if not title:
                title = f"Telegram_{url.split('/')[-1]}"

            # Sanitize title
            title = re.sub(r'[<>:"/\\|?*]', "", title)

            return {
                "title": title,
                "thumbnail": None,
                "duration": "N/A",
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
                "url": url,
            }

        except Exception as e:
            logger.error(f"Telegram extraction error: {e}")
            return None
