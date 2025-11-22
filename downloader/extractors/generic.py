import logging
import re
import requests
from typing import Optional, Dict, Any
from urllib.parse import unquote, urlparse

logger = logging.getLogger(__name__)

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

            # If it's HTML, it's probably not a direct file
            # However, check file extension as fallback in case of wrong Content-Type
            if "text/html" in content_type:
                # Check if URL path has a non-html extension
                path = urlparse(url).path
                ext = path.split('.')[-1].lower() if '.' in path else ''
                # If has video/audio/archive extension, trust the URL over Content-Type
                if ext not in ('mp4', 'webm', 'mkv', 'avi', 'mov', 'mp3', 'wav', 'flac', 'm4a', 'zip', 'rar', '7z', 'tar', 'gz'):
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
