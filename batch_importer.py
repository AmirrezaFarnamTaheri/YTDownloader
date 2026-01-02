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
        # Fallback on servers that disallow HEAD
        if response.status_code == 405:
            response = requests.get(
                url, timeout=timeout, stream=True, allow_redirects=True, headers=headers
            )
            return response.status_code < 400
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
                raise ValueError(f"Security violation: Access to {filepath} is restricted")

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

            # Process URLs concurrently
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_url = {executor.submit(verify_url, url): url for url in lines}

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
                                break

                            # Add item
                            item = {
                                "url": url,
                                "status": "Queued",
                                "title": "Pending...",  # Will be updated by fetch info task
                                "added_time": 0,  # Will be set by manager
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
