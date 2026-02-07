"""
Batch Importer.
Handles importing URLs from text files.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from downloader.types import DownloadStatus
from ui_utils import is_safe_path

logger = logging.getLogger(__name__)


class BatchImporter:
    """
    Imports URLs from a text file, verifies them, and adds them to the queue.
    """

    def __init__(self, queue_manager, config):
        self.queue_manager = queue_manager
        self.config = config
        self.max_workers = 5  # Concurrent verification
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )

    def verify_url(self, url: str, timeout: int = 3) -> bool:
        """
        Verify if a URL is reachable using a HEAD request.
        """
        try:
            response = self.session.head(url, timeout=timeout, allow_redirects=True)
            return response.status_code < 400
        except requests.RequestException:
            return False

    def import_from_file(self, filepath: str) -> tuple[int, bool]:
        """
        Reads URLs from the file, verifies them, and adds valid ones to the queue.
        Returns a tuple: (added_count, was_truncated)
        """
        added_count = 0
        was_truncated = False

        # Internal summary for logging/debugging (and potential future use)
        # summary = {"total": 0, "added": 0, "failed": 0, "errors": []}

        try:
            path = Path(filepath)
            if not path.exists() or not path.is_file():
                logger.error("File not found: %s", filepath)
                return 0, False

            # Security check
            if not is_safe_path(str(path)):
                logger.error("Access to this file is restricted: %s", filepath)
                raise ValueError(
                    f"Security violation: Access to {filepath} is restricted"
                )

            if path.suffix.lower() != ".txt":
                logger.error("Only .txt files are supported.")
                return 0, False

            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

            if not lines:
                return 0, False

            # Limit to prevent abuse
            max_batch_size = 100
            if len(lines) > max_batch_size:
                lines = lines[:max_batch_size]
                was_truncated = True

            # Pre-filter syntactically invalid URLs
            # Avoid circular import at top level if ui_utils imports something else
            from ui_utils import validate_url

            valid_syntax = []
            for url in lines:
                if validate_url(url):
                    valid_syntax.append(url)
                else:
                    logger.warning("Skipping invalid URL syntax: %s", url)

            # Process URLs concurrently
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Type hint for futures to avoid mypy confusion if it misinfers
                future_to_url: dict[Any, str] = {
                    executor.submit(self.verify_url, url): url for url in valid_syntax
                }

                queue_full = False

                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        is_valid = future.result()
                        if is_valid:
                            if (
                                self.queue_manager.get_queue_count()
                                >= self.queue_manager.MAX_QUEUE_SIZE
                            ):
                                logger.warning(
                                    "Queue is full, skipping remaining batch items"
                                )
                                queue_full = True
                                break

                            # Add item
                            dl_path = self.config.get("download_path")
                            output_template = self.config.get(
                                "output_template", "%(title)s.%(ext)s"
                            )

                            item = {
                                "url": url,
                                "status": DownloadStatus.QUEUED,
                                "title": "Pending...",
                                "added_time": 0,
                                "output_path": dl_path,
                                "output_template": output_template,
                                "video_format": self.config.get("video_format", "best"),
                                "proxy": self.config.get("proxy"),
                                "rate_limit": self.config.get("rate_limit"),
                                "sponsorblock": self.config.get("sponsorblock", False),
                                "use_aria2c": self.config.get("use_aria2c", False),
                                "gpu_accel": self.config.get("gpu_accel", "None"),
                                "cookies_from_browser": self.config.get("cookies"),
                            }
                            self.queue_manager.add_item(item)
                            added_count += 1
                        else:
                            pass  # Failed validation
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        logger.error("Error verifying %s: %s", url, exc)

                if queue_full:
                    for f in future_to_url:
                        f.cancel()

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Batch import failed: %s", e, exc_info=True)
            return added_count, was_truncated

        return added_count, was_truncated
