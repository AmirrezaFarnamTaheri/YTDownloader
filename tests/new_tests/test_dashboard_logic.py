"""
Tests for Dashboard logic.
"""

import unittest
from unittest.mock import MagicMock, patch

from views.dashboard_view import DashboardView


class TestDashboardLogic(unittest.TestCase):
    def setUp(self):
        self.mock_queue = MagicMock()
        self.view = DashboardView(
            MagicMock(), MagicMock(), MagicMock(), self.mock_queue
        )
        self.view.page = MagicMock()
        self.view.update = MagicMock()

    def test_refresh_stats_queue(self):
        self.mock_queue.get_statistics.return_value = {
            "downloading": 2,
            "queued": 5,
            "completed": 10,
        }

        self.view._refresh_stats()

        self.assertEqual(self.view.active_downloads_text.value, "2")
        self.assertEqual(self.view.queued_downloads_text.value, "5")
        self.assertEqual(self.view.completed_downloads_text.value, "10")

    @patch("views.dashboard_view.HistoryManager")
    def test_refresh_history(self, MockHistoryManager):
        MockHistoryManager.get_history.return_value = [{"title": "A"}, {"title": "B"}]

        self.view._refresh_history()

        self.assertEqual(len(self.view.recent_history_list.controls), 2)

    @patch("views.dashboard_view.shutil.disk_usage")
    def test_refresh_storage(self, mock_usage):
        mock_usage.return_value = (100, 40, 60)  # total, used, free

        self.view._refresh_storage()

        # Check pie chart sections
        self.assertEqual(len(self.view.storage_chart.sections), 2)
        # Assuming values are passed directly (scaled or raw)
        # Section 0 is free, Section 1 is used in implementation
        self.assertEqual(self.view.storage_chart.sections[0].value, 60)
        self.assertEqual(self.view.storage_chart.sections[1].value, 40)


if __name__ == "__main__":
    unittest.main()
