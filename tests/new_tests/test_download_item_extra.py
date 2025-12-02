import unittest
from unittest.mock import MagicMock

import flet as ft

from views.components.download_item import DownloadItemControl


class TestDownloadItemExtra(unittest.TestCase):
    def test_update_actions_with_page(self):
        item = {"url": "http://example.com", "status": "Queued", "title": "Test"}
        on_cancel = MagicMock()
        on_remove = MagicMock()
        on_reorder = MagicMock()

        control = DownloadItemControl(item, on_cancel, on_remove, on_reorder)

        # Mock the page attribute of actions_row
        control.actions_row.page = MagicMock()

        # Mock the update method of actions_row to avoid actual Flet logic
        control.actions_row.update = MagicMock()

        # Trigger update actions via _update_actions
        control._update_actions()

        # Verify update was called
        control.actions_row.update.assert_called()


if __name__ == "__main__":
    unittest.main()
