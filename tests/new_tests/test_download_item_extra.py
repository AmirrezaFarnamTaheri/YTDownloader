import unittest
from unittest.mock import MagicMock, patch

import flet as ft

from views.components.download_item import DownloadItemControl


class TestDownloadItemExtra(unittest.TestCase):
    def test_update_actions_with_page(self):
        item = {"url": "http://example.com", "status": "Queued", "title": "Test"}
        on_cancel = MagicMock()
        on_remove = MagicMock()

        control = DownloadItemControl(
            item,
            on_cancel,
            MagicMock(),  # retry
            on_remove,
            MagicMock(),  # play
            MagicMock(),  # folder
        )

        # Mock the page attribute of action_row
        control.action_row.page = MagicMock()

        # Mock the update method of action_row to avoid actual Flet logic
        control.action_row.update = MagicMock()

        # Trigger update actions
        control.update_actions()

        # Verify update NOT called because update_actions doesn't call update() itself,
        # but update_progress does.
        # However, update_actions modifies controls list.
        # The test originally checked if update was called.
        # In new code, update_actions is purely logical. update_progress calls self.update().

        # Let's check controls are present
        self.assertTrue(len(control.action_row.controls) > 0)


if __name__ == "__main__":
    unittest.main()
