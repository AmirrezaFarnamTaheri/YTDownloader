"""
Batch importer for download items.
"""

import concurrent.futures
import logging
from pathlib import Path

import requests

from ui_utils import get_default_download_path, is_safe_path, validate_url

logger = logging.getLogger(__name__)


def verify_url(url: str, timeout: int = 3) -> bool:
    """
    Verify if a URL is reachable using a HEAD request.
    Returns True if the URL is reachable (status code < 400), False otherwise.
    """
    try:
        # Use a user agent to avoid being blocked by some servers
        headers = {"User-Agent": "StreamCatch/2.0.0"}
        response = requests.head(
            url, timeout=timeout, allow_redirects=True, headers=headers
        )
        return response.status_code < 400
    except requests.RequestException:
        return False


# pylint: disable=too-few-public-methods
class BatchImporter:
    """Handles importing URLs from files."""

    def __init__(self, queue_manager, config):
        self.queue_manager = queue_manager
        self.config = config

    def import_from_file(self, filepath: str) -> tuple[int, bool]:
        """
        Import URLs from a text file.
        Returns a tuple of (number of items imported, whether the list was truncated).
        """
        try:
            path = Path(filepath)
            if not path.exists() or not path.is_file():
                raise ValueError("Invalid file path")

            if not is_safe_path(filepath):
                raise ValueError(
                    "Security: Batch import file must be located within your home directory"
                )

            if path.suffix.lower() not in [".txt", ".csv"]:
                raise ValueError("Invalid file type. Only .txt and .csv are allowed")

            with open(filepath, encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]

            max_batch = 100
            truncated = False
            if len(urls) > max_batch:
                urls = urls[:max_batch]
                truncated = True

            preferred_path = None
            output_template = "%(title)s.%(ext)s"
            proxy = None
            rate_limit = None

            if hasattr(self.config, "get"):
                preferred_path = self.config.get("download_path") or None
                output_template = self.config.get(
                    "output_template", "%(title)s.%(ext)s"
                )
                proxy = self.config.get("proxy") or None
                rate_limit = self.config.get("rate_limit") or None

            dl_path = get_default_download_path(preferred_path)
            count = 0
            invalid = 0

            # Filter syntactically valid URLs first
            valid_syntax_urls = []
            for url in urls:
                if validate_url(url):
                    valid_syntax_urls.append(url)
                else:
                    invalid += 1
                    logger.warning("Skipping invalid URL syntax: %s", url)

            # Verify reachability in parallel
            verified_urls = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                # Map URLs to futures
                future_to_url = {
                    executor.submit(verify_url, url): url for url in valid_syntax_urls
                }

                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        is_reachable = future.result()
                        if is_reachable:
                            verified_urls.append(url)
                        else:
                            invalid += 1
                            logger.warning("URL unreachable: %s", url)
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        logger.warning("Error verifying URL %s: %s", url, exc)
                        invalid += 1

            # Add verified URLs to queue
            for url in verified_urls:
                item = {
                    "url": url,
                    "title": url,
                    "status": "Queued",
                    "scheduled_time": None,
                    "video_format": "best",
                    "output_path": dl_path,
                    "playlist": False,
                    "sponsorblock": False,
                    "use_aria2c": self.config.get("use_aria2c", False),
                    "gpu_accel": self.config.get("gpu_accel", "None"),
                    "output_template": output_template,
                    "start_time": None,
                    "end_time": None,
                    "force_generic": False,
                    "cookies_from_browser": None,
                    "proxy": proxy,
                    "rate_limit": rate_limit,
                }
                self.queue_manager.add_item(item)
                count += 1

            if invalid:
                logger.info("Batch import skipped %d invalid/unreachable URLs", invalid)
            logger.info(
                "Batch import completed: %d items (truncated=%s)", count, truncated
            )
            return count, truncated

        except Exception as ex:
            logger.error("Failed to import batch file: %s", ex, exc_info=True)
            raise
