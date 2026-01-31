"""
Tests for History View UI logic.
"""

import unittest
from unittest.mock import MagicMock, patch

from views.history_view import HistoryView


class TestHistoryViewUI(unittest.TestCase):
    def setUp(self):
        self.view = HistoryView()
        self.view.page = MagicMock()
        self.view.update = MagicMock()

    @patch("views.history_view.HistoryManager")
    def test_load_initial(self, MockHistoryManager):
        MockHistoryManager.get_history.return_value = [{"id": 1, "title": "Test"}]

        self.view.load()

        MockHistoryManager.get_history.assert_called_with(limit=50, offset=0, search_query="")
        self.assertEqual(len(self.view.history_list.controls), 1)
        self.view.load_more_btn.visible = False # 1 < 50

    @patch("views.history_view.HistoryManager")
    def test_search_submit(self, MockHistoryManager):
        self.view.search_field.value = "query"
        MockHistoryManager.get_history.return_value = []

        self.view._on_search_submit(None)

        self.assertEqual(self.view.current_search, "query")
        self.assertEqual(self.view.offset, 0)
        MockHistoryManager.get_history.assert_called_with(limit=50, offset=0, search_query="query")

    @patch("views.history_view.HistoryManager")
    def test_load_more(self, MockHistoryManager):
        # Initial load
        MockHistoryManager.get_history.return_value = [{"id": i} for i in range(50)]
        self.view.load()
        self.assertTrue(self.view.load_more_btn.visible)

        # Load more
        self.view._load_more(None)

        self.assertEqual(self.view.offset, 50)
        MockHistoryManager.get_history.assert_called_with(limit=50, offset=50, search_query="")

if __name__ == "__main__":
    unittest.main()
