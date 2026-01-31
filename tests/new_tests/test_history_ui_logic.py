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

    @patch("app_state.state")
    def test_load_initial(self, mock_state):
        mock_hm = MagicMock()
        mock_state.history_manager = mock_hm
        mock_hm.get_history.return_value = [{"id": 1, "title": "Test"}]

        self.view.load()

        mock_hm.get_history.assert_called_with(
            limit=50, offset=0, search_query=""
        )
        self.assertEqual(len(self.view.history_list.controls), 1)
        self.view.load_more_btn.visible = False  # 1 < 50

    @patch("app_state.state")
    def test_search_submit(self, mock_state):
        mock_hm = MagicMock()
        mock_state.history_manager = mock_hm
        self.view.search_field.value = "query"
        mock_hm.get_history.return_value = []

        self.view._on_search_submit(None)

        self.assertEqual(self.view.current_search, "query")
        self.assertEqual(self.view.offset, 0)
        mock_hm.get_history.assert_called_with(
            limit=50, offset=0, search_query="query"
        )

    @patch("app_state.state")
    def test_load_more(self, mock_state):
        mock_hm = MagicMock()
        mock_state.history_manager = mock_hm
        # Initial load
        mock_hm.get_history.return_value = [{"id": i} for i in range(50)]
        self.view.load()
        self.assertTrue(self.view.load_more_btn.visible)

        # Load more
        self.view._load_more(None)

        self.assertEqual(self.view.offset, 50)
        mock_hm.get_history.assert_called_with(
            limit=50, offset=50, search_query=""
        )


if __name__ == "__main__":
    unittest.main()
