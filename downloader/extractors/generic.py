"""
Generic extractor module.
Fallback for unsupported URLs or direct file links.
"""

import os
from typing import Any, Dict, Optional

import requests


class GenericExtractor:
    """
    Generic extractor.
    """

    @staticmethod
    def get_metadata(url: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to get metadata via HEAD request.
        """
        try:
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
        except Exception:
            # Fallback
            return {"title": url, "webpage_url": url, "extractor": "generic"}
