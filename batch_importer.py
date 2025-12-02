"""
Batch importer for download items.
"""

import logging
from typing import List, Optional

import flet as ft

from ui_utils import get_default_download_path

logger = logging.getLogger(__name__)


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
            with open(filepath, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]

            max_batch = 100
            truncated = False
            if len(urls) > max_batch:
                urls = urls[:max_batch]
                truncated = True

            dl_path = get_default_download_path()
            count = 0
            for url in urls:
                if not url:
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
                    "output_template": "%(title)s.%(ext)s",
                    "start_time": None,
                    "end_time": None,
                    "force_generic": False,
                    "cookies_from_browser": None,
                }
                self.queue_manager.add_item(item)
                count += 1
            return count, truncated

        except Exception as ex:
            logger.error("Failed to import batch file: %s", ex, exc_info=True)
            raise ex
