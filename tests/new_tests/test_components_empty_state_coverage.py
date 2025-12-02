import unittest
from unittest.mock import MagicMock, patch

import flet as ft

from views.components.empty_state import EmptyState
from theme import Theme


class TestEmptyStateCoverage(unittest.TestCase):
    def test_empty_state_init(self):
        # Mock flet to prevent UI errors during initialization if needed
        # But EmptyState is a simple container, should be fine.

        icon_name = ft.Icons.DOWNLOAD
        message = "Nothing here"

        es = EmptyState(icon=icon_name, message=message)

        self.assertTrue(es.expand)
        self.assertEqual(es.alignment, ft.alignment.center)

        col = es.content
        self.assertIsInstance(col, ft.Column)
        self.assertEqual(len(col.controls), 2)

        icon = col.controls[0]
        self.assertIsInstance(icon, ft.Icon)
        self.assertEqual(icon.name, icon_name)
        self.assertEqual(icon.size, 64)

        text = col.controls[1]
        self.assertIsInstance(text, ft.Text)
        self.assertEqual(text.value, message)
        self.assertEqual(text.size, 18)
