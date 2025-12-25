"""
Batch importer for download items.
"""

import logging
from pathlib import Path
from typing import Tuple

from ui_utils import get_default_download_path, is_safe_path, validate_url

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class BatchImporter:
    """Handles importing URLs from files."""

    def __init__(self, queue_manager, config):
        self.queue_manager = queue_manager
        self.config = config

    def import_from_file(self, filepath: str) -> Tuple[int, bool]:
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

            with open(filepath, "r", encoding="utf-8") as f:
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
            for url in urls:
                if not url:
                    continue
                if not validate_url(url):
                    invalid += 1
                    logger.warning("Skipping invalid URL in batch import: %s", url)
                    continue
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
                logger.info("Batch import skipped %d invalid URLs", invalid)
            logger.info(
                "Batch import completed: %d items (truncated=%s)", count, truncated
            )
            return count, truncated

        except Exception as ex:
            logger.error("Failed to import batch file: %s", ex, exc_info=True)
            raise
