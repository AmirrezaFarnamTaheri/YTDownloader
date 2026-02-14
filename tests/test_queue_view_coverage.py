# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Coverage tests for QueueView.
"""

import unittest
from unittest.mock import MagicMock, patch

import flet as ft

from views.queue_view import QueueView


class TestQueueViewCoverage(unittest.TestCase):
    """Test suite for QueueView."""

    def setUp(self):
        self.mock_queue_manager = MagicMock()
        self.mock_page = MagicMock()

        self.view = QueueView(
            self.mock_queue_manager,
            on_cancel=MagicMock(),
            on_remove=MagicMock(),
            on_reorder=MagicMock(),
            on_play=MagicMock(),
            on_open_folder=MagicMock(),
        )
        self.view.page = self.mock_page

    def test_init(self):
        """Test QueueView initialization."""
        self.assertEqual(self.view.queue_manager, self.mock_queue_manager)
        self.assertIsInstance(self.view.list_view, ft.ListView)

    def test_rebuild_empty(self):
        """Test rebuilding view with empty queue."""
        self.mock_queue_manager.get_all.return_value = []
        self.view.rebuild()

        self.assertEqual(len(self.view.list_view.controls), 1)
        # Check if container (empty view) is added
        self.assertIsInstance(self.view.list_view.controls[0], ft.Container)

    @patch("views.queue_view.DownloadItemControl")
    def test_rebuild_items(self, mock_item_control):
        """Test rebuilding view with items."""
        items = [{"id": "1", "title": "Test"}]
        self.mock_queue_manager.get_all.return_value = items

        self.view.rebuild()

        self.assertEqual(len(self.view.list_view.controls), 1)
        mock_item_control.assert_called()

    def test_select_item(self):
        """Test item selection logic."""
        # pylint: disable=import-outside-toplevel
        from views.components.download_item import DownloadItemControl

        # Create minimal mock that pretends to be the class
        ctrl1 = MagicMock()
        ctrl1.__class__ = DownloadItemControl
        ctrl2 = MagicMock()
        ctrl2.__class__ = DownloadItemControl

        self.view.list_view.controls = [ctrl1, ctrl2]
        self.view.list_view.scroll_to = MagicMock()

        self.view.select_item(1)

        self.assertEqual(self.view.selected_index, 1)
        # Verify scroll
        self.view.list_view.scroll_to.assert_called()

    def test_get_selected_item(self):
        """Test retrieving the selected item."""
        # pylint: disable=import-outside-toplevel
        from views.components.download_item import DownloadItemControl

        ctrl = MagicMock()
        ctrl.__class__ = DownloadItemControl
        ctrl.item = {"id": "1"}

        self.view.list_view.controls = [ctrl]
        self.view.selected_index = 0

        item = self.view.get_selected_item()
        self.assertEqual(item, {"id": "1"})

        self.view.selected_index = 5
        self.assertIsNone(self.view.get_selected_item())

    def test_clear_completed_uses_queue_manager_api(self):
        """Test clearing completed items via QueueManager.clear_completed."""
        self.mock_queue_manager.clear_completed.return_value = 2

        self.view._on_clear_completed(None)

        self.mock_queue_manager.clear_completed.assert_called_once()
        self.mock_page.open.assert_called()

    def test_pause_all_action(self):
        """Test pause-all action delegates to queue manager."""
        self.mock_queue_manager.pause_all.return_value = 3

        self.view._on_pause_all(None)

        self.mock_queue_manager.pause_all.assert_called_once()
        self.mock_page.open.assert_called()

    def test_resume_all_action(self):
        """Test resume-all action delegates to queue manager."""
        self.mock_queue_manager.resume_all.return_value = 1

        self.view._on_resume_all(None)

        self.mock_queue_manager.resume_all.assert_called_once()
        self.mock_page.open.assert_called()
