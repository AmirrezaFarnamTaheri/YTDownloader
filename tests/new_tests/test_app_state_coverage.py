"""
Tests for AppState coverage.
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from app_state import AppState


class TestAppStateCoverage(unittest.TestCase):
    """Test suite for AppState coverage."""

    def setUp(self):
        """Reset singleton before each test."""
        # pylint: disable=protected-access
        AppState._instance = None

    def tearDown(self):
        """Clean up singleton after each test."""
        # pylint: disable=protected-access
        if AppState._instance:
            AppState._instance.cleanup()
        AppState._instance = None

    def test_singleton(self):
        """Test singleton pattern."""
        app1 = AppState()
        app2 = AppState()
        self.assertIs(app1, app2)

    def test_cache_logic(self):
        """Test video info cache logic (LRU)."""
        app = AppState()
        # Set max size small for testing
        # pylint: disable=protected-access
        app._video_info_max_size = 2

        app.set_video_info("url1", {"title": "1"})
        app.set_video_info("url2", {"title": "2"})

        self.assertEqual(app.get_video_info("url1")["title"], "1")
        self.assertEqual(app.get_video_info("url2")["title"], "2")

        # Add 3rd, should evict url1 (oldest)
        app.set_video_info("url3", {"title": "3"})

        self.assertIsNone(app.get_video_info("url1"))
        self.assertEqual(app.get_video_info("url2")["title"], "2")
        self.assertEqual(app.get_video_info("url3")["title"], "3")

        app.clear_video_info_cache()
        self.assertIsNone(app.get_video_info("url2"))

    @patch("app_state.SocialManager")
    def test_social_connection(self, mock_social_manager):
        """Test social manager connection."""
        # Mock social manager instance
        mock_social = mock_social_manager.return_value

        app = AppState()

        # Wait for thread to run
        time.sleep(0.5)

        # Verify connect called
        mock_social.connect.assert_called_once()

        # Cleanup should close
        app.cleanup()
        mock_social.close.assert_called_once()

    def test_safe_social_connect_failure(self):
        """Test safe social connection failure."""
        with patch("app_state.SocialManager") as mock_social:
            mock_instance = mock_social.return_value
            mock_instance.connect.side_effect = Exception("Connection fail")

            app = AppState()
            time.sleep(0.2)
            # Should not crash
            # pylint: disable=protected-access
            self.assertTrue(app._initialized)

    def test_cleanup_failure(self):
        """Test cleanup failure handling."""
        app = AppState()
        app.social_manager = MagicMock()
        app.social_manager.close.side_effect = Exception("Close fail")

        # Should not raise
        app.cleanup()
