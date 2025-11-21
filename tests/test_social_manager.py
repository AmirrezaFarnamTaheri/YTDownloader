import unittest
from unittest.mock import MagicMock, patch
from social_manager import SocialManager


class TestSocialManager(unittest.TestCase):

    @patch("social_manager.time")
    @patch.dict("sys.modules", {"pypresence": MagicMock()})
    def test_connect_success(self, mock_time):
        # Mock pypresence.Presence
        with patch("pypresence.Presence") as MockPresence:
            mock_rpc = MockPresence.return_value

            manager = SocialManager(client_id="123")
            manager.connect()

            self.assertTrue(manager.connected)
            MockPresence.assert_called_with("123")
            mock_rpc.connect.assert_called_once()

    @patch.dict("sys.modules", {"pypresence": MagicMock()})
    def test_connect_already_connected(self):
        with patch("pypresence.Presence") as MockPresence:
            manager = SocialManager()
            manager.connected = True
            manager.connect()

            MockPresence.assert_not_called()

    def test_connect_import_error(self):
        # Simulate ImportError by ensuring pypresence cannot be imported
        with patch.dict("sys.modules", {"pypresence": None}):
            # We patch the constructor logic if possible, but here we rely on
            # mock.dict above to make 'from pypresence import Presence' fail or return Mock
            # Actually, 'from pypresence import Presence' inside the method needs to fail.
            # If we mock sys.modules, imports might succeed with a Mock object.
            # To force ImportError, we can set side_effect on __import__ or just rely on logic.
            # Since pypresence is in requirements, it is installed.
            # So we must force failure.
            with patch("builtins.__import__", side_effect=ImportError):
                manager = SocialManager()
                manager.connect()
                self.assertFalse(manager.connected)

    @patch("social_manager.time")
    @patch.dict("sys.modules", {"pypresence": MagicMock()})
    def test_connect_exception(self, mock_time):
        with patch("pypresence.Presence") as MockPresence:
            mock_rpc = MockPresence.return_value
            mock_rpc.connect.side_effect = Exception("Connection failed")

            manager = SocialManager()
            manager.connect()

            self.assertFalse(manager.connected)

    @patch("social_manager.time")
    @patch.dict("sys.modules", {"pypresence": MagicMock()})
    def test_update_status_success(self, mock_time):
        mock_time.time.return_value = 1000
        with patch("pypresence.Presence") as MockPresence:
            mock_rpc = MockPresence.return_value

            manager = SocialManager()
            manager.connect()
            manager.update_status("Downloading", "Video 1")

            mock_rpc.update.assert_called_with(
                state="Downloading",
                details="Video 1",
                large_image="logo",
                large_text="StreamCatch",
                start=1000,
            )

    def test_update_status_not_connected(self):
        manager = SocialManager()
        manager.connected = False
        manager.rpc = MagicMock()

        manager.update_status("State")
        manager.rpc.update.assert_not_called()

    @patch("social_manager.time")
    @patch.dict("sys.modules", {"pypresence": MagicMock()})
    def test_update_status_exception(self, mock_time):
        with patch("pypresence.Presence") as MockPresence:
            mock_rpc = MockPresence.return_value
            mock_rpc.update.side_effect = Exception("Update failed")

            manager = SocialManager()
            manager.connect()
            manager.update_status("State")

            self.assertFalse(manager.connected)

    @patch.dict("sys.modules", {"pypresence": MagicMock()})
    def test_close(self):
        with patch("pypresence.Presence") as MockPresence:
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
