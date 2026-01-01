"""
Tests for UI extended functionality.
"""
import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock flet if needed
try:
    import flet as ft
except ImportError:
    pass

from app_layout import AppLayout


class TestUIExtended(unittest.TestCase):
    """Test extended UI features."""

    def test_app_layout_resize(self):
        """Test AppLayout resize handler."""
        page_mock = MagicMock()
        layout = AppLayout(page_mock, lambda e: None)

        # Test Compact Mode Trigger
        layout.toggle_compact_mode = MagicMock()
        layout.rail.extended = True

        # Width < 1000 -> Should toggle compact True
        layout.handle_resize(900, 600)
        layout.toggle_compact_mode.assert_called_with(True)

        # Reset
        layout.toggle_compact_mode.reset_mock()
        layout.rail.extended = False # Already compact

        # Width < 1000 -> Should NOT toggle again
        layout.handle_resize(900, 600)
        layout.toggle_compact_mode.assert_not_called()

        # Test Expand Trigger
        layout.rail.extended = False # Compact

        # Width >= 1000 -> Should toggle compact False (expand)
        layout.handle_resize(1200, 800)
        layout.toggle_compact_mode.assert_called_with(False)

        # Reset
        layout.toggle_compact_mode.reset_mock()
        layout.rail.extended = True # Already expanded

        # Width >= 1000 -> Should NOT toggle
        layout.handle_resize(1200, 800)
        layout.toggle_compact_mode.assert_not_called()
