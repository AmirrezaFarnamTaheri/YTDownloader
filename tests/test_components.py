import os
import sys
import threading
import unittest
from unittest.mock import ANY, MagicMock, patch

# Adjust path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import flet as ft

from components import DownloadItemControl


class TestDownloadItemControl(unittest.TestCase):
    def setUp(self):
        self.item = {"url": "http://test", "status": "Queued", "title": "Test Video"}
        self.on_cancel = MagicMock()
        self.on_remove = MagicMock()
        self.on_reorder = MagicMock()

    def test_init(self):
        control = DownloadItemControl(
            self.item, self.on_cancel, self.on_remove, self.on_reorder
        )
        self.assertEqual(control.item, self.item)
        self.assertIsInstance(control.view, ft.Container)

    def test_update_progress(self):
        control = DownloadItemControl(
            self.item, self.on_cancel, self.on_remove, self.on_reorder
        )
        self.item["status"] = "Downloading"
        self.item["speed"] = "1MB/s"
        self.item["size"] = "10MB"
        self.item["eta"] = "10s"

        # Mock update method of controls inside because we can't really call update() in headless test without page
        control.status_text.update = MagicMock()
        control.details_text.update = MagicMock()
        control.progress_bar.update = MagicMock()
        control.title_text.update = MagicMock()
        if hasattr(control, "actions_row") and control.actions_row.page:
            control.actions_row.update = MagicMock()

        control.update_progress()

        self.assertEqual(control.status_text.value, "Downloading")
        self.assertIn("1MB/s", control.details_text.value)


if __name__ == "__main__":
    unittest.main()
