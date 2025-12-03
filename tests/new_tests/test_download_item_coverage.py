import unittest
from unittest.mock import MagicMock, patch

import flet as ft

from views.components.download_item import DownloadItemControl


class TestDownloadItemControlCoverage(unittest.TestCase):
    def test_build_and_init(self):
        item = {
            "url": "http://example.com/video.mp4",
            "status": "Queued",
            "title": "My Video",
        }

        control = DownloadItemControl(
            item=item,
            on_cancel=MagicMock(),
            on_remove=MagicMock(),
            on_retry=MagicMock(),
            on_play=MagicMock(),
            on_open_folder=MagicMock(),
        )

        self.assertIsInstance(control.content, ft.Column)
        self.assertEqual(control.title_text.value, "My Video")

        # Check defaults
        self.assertEqual(control.progress_bar.value, 0)

    def test_icon_logic(self):
        cases = [
            ("https://youtube.com/v/123", ft.Icons.VIDEO_LIBRARY),
            ("https://instagram.com/p/123", ft.Icons.PHOTO_CAMERA),
            ("https://x.com/user/status/123", ft.Icons.ALTERNATE_EMAIL),
            ("http://other.com", ft.Icons.LINK),
        ]

        for url, expected_icon in cases:
            item = {"url": url, "status": "Queued"}
            control = DownloadItemControl(
                item,
                MagicMock(),
                MagicMock(),
                MagicMock(),
                MagicMock(),
                MagicMock()
            )

            # Icon is inside the first Row -> Icon is first child
            main_col = control.content
            top_row = main_col.controls[0]
            icon = top_row.controls[0]

            self.assertEqual(icon.name, expected_icon, f"Failed for {url}")

    def test_update_actions_logic(self):
        # Downloading state -> Cancel button
        item = {"url": "http://test", "status": "Downloading"}
        control = DownloadItemControl(
            item, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        actions = control.action_row.controls
        # Should have Cancel (icon CANCEL)
        self.assertTrue(
            any(
                isinstance(c, ft.IconButton) and c.icon == ft.Icons.CANCEL
                for c in actions
            )
        )

        # Error state -> Retry and Remove
        item = {"url": "http://test", "status": "Error"}
        control = DownloadItemControl(
            item, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        actions = control.action_row.controls
        self.assertTrue(
            any(
                isinstance(c, ft.IconButton) and c.icon == ft.Icons.REFRESH
                for c in actions
            )
        )
        self.assertTrue(
            any(
                isinstance(c, ft.IconButton) and c.icon == ft.Icons.DELETE_OUTLINE
                for c in actions
            )
        )

        # Completed state -> Play and Open Folder
        item = {"url": "http://test", "status": "Completed"}
        control = DownloadItemControl(
            item, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        actions = control.action_row.controls
        self.assertTrue(
            any(
                isinstance(c, ft.IconButton) and c.icon == ft.Icons.PLAY_ARROW
                for c in actions
            )
        )
        self.assertTrue(
            any(
                isinstance(c, ft.IconButton) and c.icon == ft.Icons.FOLDER_OPEN
                for c in actions
            )
        )

    def test_update_progress_logic(self):
        item = {"url": "http://test", "status": "Queued"}
        control = DownloadItemControl(
            item, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )

        # Mock update methods
        control.status_text.update = MagicMock()
        control.info_text.update = MagicMock()
        control.progress_bar.update = MagicMock()
        control.title_text.update = MagicMock()
        control.action_row.update = MagicMock()
        control.update = MagicMock()

        # Downloading
        item["status"] = "Downloading"
        item["speed"] = "1 MB/s"
        item["eta"] = "10s"
        control.update_progress()
        self.assertIn("1 MB/s", control.info_text.value)

        # Completed
        item["status"] = "Completed"
        control.update_progress()
        self.assertEqual(control.progress_bar.value, 1)

        # Error
        item["status"] = "Error"
        control.update_progress()
        # Progress not reset to 0 in update_progress logic necessarily, but status color changes
        # Checking update called
        control.update.assert_called()

    def test_action_callbacks(self):
        # Test clicks trigger callbacks
        mock_cancel = MagicMock()
        mock_retry = MagicMock()
        mock_remove = MagicMock()
        mock_play = MagicMock()
        mock_folder = MagicMock()

        item = {"url": "http://test", "status": "Downloading"}
        # Signature: (item, on_cancel, on_retry, on_remove, on_play, on_open_folder)
        control = DownloadItemControl(
            item, mock_cancel, mock_retry, mock_remove, mock_play, mock_folder
        )

        # Find cancel button
        cancel_btn = next(
            c for c in control.action_row.controls if c.icon == ft.Icons.CANCEL
        )
        cancel_btn.on_click(None)
        mock_cancel.assert_called_with(item)

        # Switch to Error for Retry
        item["status"] = "Error"
        control.update_actions()
        retry_btn = next(
            c for c in control.action_row.controls if c.icon == ft.Icons.REFRESH
        )
        retry_btn.on_click(None)

        mock_retry.assert_called_with(item)

        # Remove
        remove_btn = next(
            c for c in control.action_row.controls if c.icon == ft.Icons.DELETE_OUTLINE
        )
        remove_btn.on_click(None)
        mock_remove.assert_called_with(item)

if __name__ == "__main__":
    unittest.main()
