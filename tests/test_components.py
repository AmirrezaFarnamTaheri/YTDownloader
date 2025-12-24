# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
import os
import sys
import threading
import unittest
from unittest.mock import ANY, MagicMock, patch

# Adjust path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import flet as ft

from localization_manager import LocalizationManager as LM
from views.components.download_item import DownloadItemControl


class TestDownloadItemControl(unittest.TestCase):
    def setUp(self):
        LM.load_language("en")
        self.item = {"url": "http://test", "status": "Queued", "title": "Test Video"}
        self.on_cancel = MagicMock()
        self.on_retry = MagicMock()
        self.on_remove = MagicMock()

    def test_init(self):
        control = DownloadItemControl(
            self.item,
            self.on_cancel,
            self.on_retry,
            self.on_remove,
            MagicMock(),  # on_play
            MagicMock(),  # on_open_folder
        )
        self.assertEqual(control.item, self.item)
        self.assertIsInstance(control, ft.Container)

    def test_update_progress(self):
        control = DownloadItemControl(
            self.item,
            self.on_cancel,
            self.on_retry,
            self.on_remove,
            MagicMock(),  # on_play
            MagicMock(),  # on_open_folder
        )
        self.item["status"] = "Downloading"
        self.item["speed"] = "1MB/s"
        self.item["size"] = "10MB"
        self.item["eta"] = "10s"

        # Mock update method of controls inside because we can't really call update() in headless test without page
        control.status_text.update = MagicMock()
        control.info_text.update = MagicMock()
        control.progress_bar.update = MagicMock()
        control.title_text.update = MagicMock()
        control.action_row.update = MagicMock()
        control.update = MagicMock()

        control.update_progress()

        self.assertEqual(control.status_text.value, "Downloading")
        self.assertIn("1MB/s", control.info_text.value)


if __name__ == "__main__":
    unittest.main()
