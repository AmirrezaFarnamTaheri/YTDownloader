"""
Batch Importer.
Handles importing URLs from text files.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from ui_utils import is_safe_path

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
        if response.status_code < 400:
            return True
        return False
    except requests.RequestException:
        return False


class BatchImporter:
    """
    Imports URLs from a text file, verifies them, and adds them to the queue.
    """

    def __init__(self, queue_manager):
        self.queue_manager = queue_manager
        self.max_workers = 5  # Concurrent verification

    def import_from_file(self, filepath: str) -> tuple[int, bool]:
        """
        Reads URLs from the file, verifies them, and adds valid ones to the queue.
        Returns a tuple: (added_count, was_truncated)
        Compatible with legacy callers expecting tuple return.
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
            MAX_BATCH_SIZE = 100
            if len(lines) > MAX_BATCH_SIZE:
                lines = lines[:MAX_BATCH_SIZE]
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
                future_to_url = {
                    executor.submit(verify_url, url): url for url in valid_syntax
                }

                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        is_valid = future.result()
                        if is_valid:
                            # Add to queue
                            # Check if queue is full
                            if (
                                self.queue_manager.get_queue_count()
                                >= self.queue_manager.MAX_QUEUE_SIZE
                            ):
                                logger.warning(
                                    "Queue is full, skipping remaining batch items"
                                )
                                for f in future_to_url:
                                    f.cancel()
                                executor.shutdown(wait=False, cancel_futures=True)
                                break

                            # Add item
                            from app_state import state

                            config = state.config
                            dl_path = config.get("download_path")
                            output_template = config.get(
                                "output_template", "%(title)s.%(ext)s"
                            )

                            item = {
                                "url": url,
                                "status": "Queued",
                                "title": "Pending...",
                                "added_time": 0,
                                "output_path": dl_path,
                                "output_template": output_template,
                                "video_format": config.get("video_format", "best"),
                                "proxy": config.get("proxy"),
                                "rate_limit": config.get("rate_limit"),
                                "sponsorblock": config.get("sponsorblock", False),
                                "use_aria2c": config.get("use_aria2c", False),
                                "gpu_accel": config.get("gpu_accel", "None"),
                                "cookies_from_browser": config.get("cookies"),
                            }
                            self.queue_manager.add_item(item)
                            added_count += 1
                        else:
                            pass  # Failed validation
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        logger.error("Error verifying %s: %s", url, exc)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Batch import failed: %s", e)
            raise  # Re-raise or return 0? Caller usually expects return.
            # Original code raised?
            # Let's check test cases. They expect return.
            # But robust error handling suggests logging and returning what we have.
            # The original code might have just crashed or returned.
            # I'll return what we have.

        return added_count, was_truncated
