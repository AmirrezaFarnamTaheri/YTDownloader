import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from app_state import AppState


class TestAppStateCoverage(unittest.TestCase):

    def setUp(self):
        # Reset singleton
        AppState._instance = None

    def tearDown(self):
        if AppState._instance:
            AppState._instance.cleanup()
        AppState._instance = None

    def test_singleton(self):
        app1 = AppState()
        app2 = AppState()
        self.assertIs(app1, app2)

    def test_cache_logic(self):
        app = AppState()
        # Set max size small for testing
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
    def test_social_connection(self, MockSocialManager):
        # Mock social manager instance
        mock_social = MockSocialManager.return_value

        app = AppState()

        # Wait for thread to run
        time.sleep(0.5)

        # Verify connect called
        mock_social.connect.assert_called_once()

        # Cleanup should close
        app.cleanup()
        mock_social.close.assert_called_once()

    def test_safe_social_connect_failure(self):
        with patch("app_state.SocialManager") as MockSocial:
            mock_instance = MockSocial.return_value
            mock_instance.connect.side_effect = Exception("Connection fail")

            app = AppState()
            time.sleep(0.2)
            # Should not crash
            self.assertTrue(app._initialized)

    def test_cleanup_failure(self):
        app = AppState()
        app.social_manager = MagicMock()
        app.social_manager.close.side_effect = Exception("Close fail")

        # Should not raise
        app.cleanup()
