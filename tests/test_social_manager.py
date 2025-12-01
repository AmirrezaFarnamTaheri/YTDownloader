import unittest
from unittest.mock import MagicMock, patch
import os

# Import after setting up environment if needed, but patching is better
from social_manager import SocialManager


class TestSocialManager(unittest.TestCase):

    def setUp(self):
        # Set a fake client ID so connect() doesn't skip
        self.env_patcher = patch.dict(os.environ, {"DISCORD_CLIENT_ID": "111111111111111111"})
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_connect_success(self):
        # Patch the class imported in social_manager module
        with patch("social_manager.Presence") as MockPresence:
            mock_rpc = MockPresence.return_value

            manager = SocialManager()
            manager.connect()

            self.assertTrue(manager.connected)
            MockPresence.assert_called()
            mock_rpc.connect.assert_called_once()

    def test_connect_exception(self):
        with patch("social_manager.Presence") as MockPresence:
            mock_rpc = MockPresence.return_value
            mock_rpc.connect.side_effect = Exception("Connection failed")

            manager = SocialManager()
            manager.connect()

            self.assertFalse(manager.connected)

    def test_update_activity_success(self):
        with patch("social_manager.Presence") as MockPresence:
            mock_rpc = MockPresence.return_value

            manager = SocialManager()
            manager.connect()

            manager.update_activity("Downloading", "Video 1")

            # Let's inspect call args
            args, kwargs = mock_rpc.update.call_args
            self.assertEqual(kwargs['details'], "Downloading")
            self.assertEqual(kwargs['state'], "Video 1")
            self.assertEqual(kwargs['large_image'], "logo")
            self.assertEqual(kwargs['large_text'], "StreamCatch")
            self.assertIn('start', kwargs)

    def test_update_activity_not_connected(self):
        manager = SocialManager()
        manager.connected = False
        manager.rpc = MagicMock()

        manager.update_activity("State", "Details")
        manager.rpc.update.assert_not_called()

    def test_update_activity_exception(self):
        with patch("social_manager.Presence") as MockPresence:
            mock_rpc = MockPresence.return_value
            mock_rpc.update.side_effect = Exception("Update failed")

            manager = SocialManager()
            manager.connect()
            manager.update_activity("State", "Details")

            self.assertFalse(manager.connected)

    def test_close(self):
        with patch("social_manager.Presence") as MockPresence:
            mock_rpc = MockPresence.return_value

            manager = SocialManager()
            manager.connect()
            manager.close()

            self.assertFalse(manager.connected)
            mock_rpc.close.assert_called_once()

    def test_close_exception(self):
        manager = SocialManager()
        manager.rpc = MagicMock()
        manager.rpc.close.side_effect = Exception("Close failed")
        manager.connected = True

        manager.close()

        self.assertFalse(manager.connected)
