"""
Generic extractor module.
Fallback for unsupported URLs or direct file links.
"""

import logging
import os
from typing import Any

import requests

from ui_utils import safe_request_with_redirects, validate_url

logger = logging.getLogger(__name__)


class GenericExtractor:
    """
    Generic extractor.
    """

    # pylint: disable=too-few-public-methods

    @staticmethod
    def get_metadata(url: str) -> dict[str, Any] | None:
        """
        Attempt to get metadata via HEAD request.
        """
        try:
            if not validate_url(url, resolve_host=True):
                logger.debug("Generic metadata skip: invalid URL %s", url)
                return None
            # Simple HEAD to get content type/length
            response = safe_request_with_redirects("HEAD", url, timeout=5)
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
        except requests.RequestException as exc:
            logger.debug("Generic metadata HEAD failed for %s: %s", url, exc)
            # Fallback
            return {"title": url, "webpage_url": url, "extractor": "generic"}
