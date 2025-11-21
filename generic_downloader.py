import requests
import logging
import os
import re
import time
from html.parser import HTMLParser
from typing import Optional, Dict, Any, Callable
from urllib.parse import unquote

logger = logging.getLogger(__name__)


class _TelegramHTMLParser(HTMLParser):
    """Lightweight parser to extract Telegram embed information without BeautifulSoup."""

    def __init__(self):
        super().__init__()
        self.video_src: Optional[str] = None
        self.photo_src: Optional[str] = None
        self.og_video: Optional[str] = None
        self.og_image: Optional[str] = None
        self.caption_parts = []
        self._collect_caption = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get('class', '').split()

        if tag == 'video' and not self.video_src:
            self.video_src = attrs_dict.get('src')

        if tag == 'div' and 'tgme_widget_message_photo_wrap' in classes and not self.photo_src:
            style = attrs_dict.get('style', '')
            match = re.search(r"url\('?(.*?)'?\)", style)
            if match:
                self.photo_src = match.group(1)

        if tag == 'meta':
            if attrs_dict.get('property') == 'og:video' and not self.og_video:
                self.og_video = attrs_dict.get('content')
            if attrs_dict.get('property') == 'og:image' and not self.og_image:
                self.og_image = attrs_dict.get('content')

        if tag == 'div' and 'tgme_widget_message_text' in classes:
            self._collect_caption = True

    def handle_endtag(self, tag):
        if tag == 'div' and self._collect_caption:
            self._collect_caption = False

    def handle_data(self, data):
        if self._collect_caption:
            self.caption_parts.append(data.strip())

    @property
    def caption(self) -> str:
        return " ".join(part for part in self.caption_parts if part)

    @property
    def is_video(self) -> bool:
        return bool(self.video_src or self.og_video)

    @property
    def media_extension(self) -> str:
        if self.is_video:
            return 'mp4'
        return 'jpg'

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
            # Convert standard link to embed link or s/ link to get preview content
            # Actually, just fetching the t.me link often gives a 'view in channel' page
            # but sometimes contains the Open Graph tags.
            # Let's try to fetch the embed version which is usually cleaner for scraping.
            # Format: https://t.me/channel/123?embed=1

            if "?embed=1" not in url:
                embed_url = f"{url}?embed=1"
            else:
                embed_url = url

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            logger.info(f"Scraping Telegram URL: {embed_url}")
            response = requests.get(embed_url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch Telegram page: {response.status_code}")
                return None

            parser = _TelegramHTMLParser()
            parser.feed(response.text)

            media_url = parser.video_src or parser.photo_src or parser.og_video or parser.og_image
            ext = parser.media_extension
            is_video = parser.is_video

            if not media_url:
                logger.warning("No media found on Telegram page.")
                return None

            title = parser.caption.strip()[:50] if parser.caption else "Telegram_Media"
            if not title:
                title = f"Telegram_{url.split('/')[-1]}"

            # Sanitize title
            title = re.sub(r'[<>:"/\\|?*]', '', title)

            return {
                'title': title,
                'thumbnail': None, # Could extract user avatar or og:image
                'duration': 'N/A',
                'video_streams': [{
                    'url': media_url,
                    'format_id': 'telegram_source',
                    'ext': ext,
                    'resolution': 'Original',
                    'filesize': None
                }],
                'audio_streams': [], # Usually mixed in
                'is_telegram': True,
                'url': url # Original URL
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
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            logger.info(f"Checking Generic URL: {url}")
            response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)

            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            content_length = response.headers.get('Content-Length')

            # If it's HTML, it's probably not a direct file (unless user wants to download the page)
            if 'text/html' in content_type:
                return None

            # Determine filename
            filename = "downloaded_file"
            cd = response.headers.get('Content-Disposition')
            if cd:
                # filename="abc.ext"
                fname_match = re.findall(r'filename="?([^"]+)"?', cd)
                if fname_match:
                    filename = fname_match[0]

            if filename == "downloaded_file":
                # Try from URL
                path = unquote(url.split('?')[0])
                name = path.split('/')[-1]
                if name and '.' in name:
                    filename = name

            filesize = int(content_length) if content_length else None
            ext = filename.split('.')[-1] if '.' in filename else 'dat'

            return {
                'title': filename,
                'thumbnail': None,
                'duration': 'N/A',
                'video_streams': [{
                    'url': url,
                    'format_id': 'direct_file',
                    'ext': ext,
                    'resolution': 'N/A',
                    'filesize': filesize
                }],
                'audio_streams': [],
                'is_generic': True,
                'url': url
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
    cancel_token: Any = None
):
    """
    Downloads a file using requests with streaming.
    """
    try:
        headers = {
             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Start stream
        with requests.get(url, stream=True, headers=headers, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))

            # Determine final path
            final_path = os.path.join(output_path, filename)

            downloaded = 0
            start_time = time.time()

            with open(final_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if cancel_token:
                         # Use check(d) if available, otherwise property checks
                         if hasattr(cancel_token, 'check'):
                             cancel_token.check(None) # Argument d is ignored in main.py check() anyway
                         else:
                             if getattr(cancel_token, 'cancelled', False):
                                 raise Exception("Download cancelled by user")
                             while getattr(cancel_token, 'is_paused', False):
                                 time.sleep(0.5)
                                 if getattr(cancel_token, 'cancelled', False):
                                     raise Exception("Download cancelled by user")

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Calculate speed and ETA
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        eta = (total_size - downloaded) / speed if speed > 0 and total_size > 0 else 0

                        progress_hook({
                            'status': 'downloading',
                            'downloaded_bytes': downloaded,
                            'total_bytes': total_size,
                            'speed': speed,
                            'eta': eta,
                            'filename': filename
                        }, download_item)

            progress_hook({
                'status': 'finished',
                'filename': final_path,
                'total_bytes': total_size
            }, download_item)

    except Exception as e:
        logger.error(f"Generic download error: {e}")
        raise
