"""
Generic extractor module.
Fallback for unsupported URLs or direct file links.
"""

import os
from typing import Any, Dict, Optional

import requests

from ui_utils import validate_url


class GenericExtractor:
    """
    Generic extractor.
    """

    # pylint: disable=too-few-public-methods

    @staticmethod
    def get_metadata(url: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to get metadata via HEAD request.
        """
        try:
            if not validate_url(url):
                return None
            # Simple HEAD to get content type/length
            response = requests.head(url, timeout=5, allow_redirects=True)
            content_type = response.headers.get("Content-Type", "")

            # Basic guess
            title = os.path.basename(url)
            if "?" in title:
                title = title.split("?")[0]

            return {
                "title": title,
                "webpage_url": url,
                "extractor": "generic",
                "filesize": response.headers.get("Content-Length"),
                "format": content_type,
            }
        except requests.RequestException:
            # Fallback
            return {"title": url, "webpage_url": url, "extractor": "generic"}
