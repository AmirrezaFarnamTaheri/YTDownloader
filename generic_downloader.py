import requests
import logging
import os
import re
import time
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, Callable
from urllib.parse import unquote

logger = logging.getLogger(__name__)


class TelegramExtractor:
    @staticmethod
    def is_telegram_url(url: str) -> bool:
        return "t.me/" in url or "telegram.me/" in url

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
            response = requests.get(embed_url, headers=headers, timeout=10)
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


class GenericExtractor:
    @staticmethod
    def extract(url: str) -> Optional[Dict[str, Any]]:
        """
        Performs a HEAD request to check if the URL points to a direct file.
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            logger.info(f"Checking Generic URL: {url}")

            try:
                response = requests.head(
                    url, headers=headers, allow_redirects=True, timeout=10
                )
            except requests.exceptions.RequestException:
                # HEAD failed, try GET with stream=True to avoid downloading body
                response = requests.get(
                    url, headers=headers, stream=True, timeout=10, allow_redirects=True
                )
                response.close()  # Close connection immediately

            # Check content type
            content_type = response.headers.get("Content-Type", "").lower()
            content_length = response.headers.get("Content-Length")

            # If it's HTML, it's probably not a direct file (unless user wants to download the page)
            if "text/html" in content_type:
                return None

            # Determine filename
            filename = "downloaded_file"
            cd = response.headers.get("Content-Disposition")
            if cd:
                # filename="abc.ext"
                fname_match = re.findall(r'filename="?([^"]+)"?', cd)
                if fname_match:
                    filename = fname_match[0]

            if filename == "downloaded_file":
                # Try from URL
                path = unquote(url.split("?")[0])
                name = path.split("/")[-1]
                if name and "." in name:
                    filename = name

            filesize = int(content_length) if content_length else None
            ext = filename.split(".")[-1] if "." in filename else "dat"

            return {
                "title": filename,
                "thumbnail": None,
                "duration": "N/A",
                "video_streams": [
                    {
                        "url": url,
                        "format_id": "direct_file",
                        "ext": ext,
                        "resolution": "N/A",
                        "filesize": filesize,
                    }
                ],
                "audio_streams": [],
                "is_generic": True,
                "url": url,
            }

        except Exception as e:
            logger.error(f"Generic extraction error: {e}")
            return None


def download_generic(
    url: str,
    output_path: str,
    filename: str,
    progress_hook: Callable,
    download_item: Dict[str, Any],
    cancel_token: Any = None,
):
    """
    Downloads a file using requests with streaming.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Start stream
        with requests.get(url, stream=True, headers=headers, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))

            # Determine final path
            final_path = os.path.join(output_path, filename)

            downloaded = 0
            start_time = time.time()

            with open(final_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if cancel_token and cancel_token.cancelled:
                        raise Exception("Download cancelled by user")

                    while cancel_token and cancel_token.is_paused:
                        time.sleep(0.5)
                        if cancel_token.cancelled:
                            raise Exception("Download cancelled by user")

                    # Handle pause if available on token (some implementations might not have it)
                    if cancel_token and hasattr(cancel_token, 'is_paused'):
                         while cancel_token.is_paused:
                             time.sleep(0.5)
                             if hasattr(cancel_token, 'cancelled') and cancel_token.cancelled:
                                 raise Exception("Download cancelled by user")

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Calculate speed and ETA
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        eta = (
                            (total_size - downloaded) / speed
                            if speed > 0 and total_size > 0
                            else 0
                        )

                        progress_hook(
                            {
                                "status": "downloading",
                                "downloaded_bytes": downloaded,
                                "total_bytes": total_size,
                                "speed": speed,
                                "eta": eta,
                                "filename": filename,
                            },
                            download_item,
                        )

            progress_hook(
                {
                    "status": "finished",
                    "filename": final_path,
                    "total_bytes": total_size,
                },
                download_item,
            )

    except Exception as e:
        logger.error(f"Generic download error: {e}")
        raise
