import unittest
from unittest.mock import MagicMock
import flet as ft
from components.download_item import DownloadItemControl


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
            on_reorder=MagicMock(),
            on_retry=MagicMock(),
            is_selected=False,
        )

        self.assertIsInstance(control.view, ft.Container)
        self.assertEqual(control.title_text.value, "My Video")

        # Check defaults
        self.assertEqual(control.progress_bar.value, 0)

    def test_icon_logic(self):
        cases = [
            ("https://youtube.com/v/123", ft.Icons.ONDEMAND_VIDEO),
            ("https://t.me/channel/123", ft.Icons.TELEGRAM),
            ("https://x.com/user/status/123", ft.Icons.ALTERNATE_EMAIL),
            ("https://instagram.com/p/123", ft.Icons.CAMERA_ALT),
            ("http://other.com", ft.Icons.INSERT_DRIVE_FILE),
        ]

        for url, expected_icon in cases:
            item = {"url": url, "status": "Queued"}
            control = DownloadItemControl(item, MagicMock(), MagicMock(), MagicMock())
            # We need to dig into the view structure to check the icon
            # Structure: Container -> Row -> [IconContainer -> Icon, ...]
            # IconContainer is index 0 in main Row
            # Icon is content of IconContainer
            icon_container = control.view.content.controls[0]
            icon = icon_container.content
            self.assertEqual(icon.name, expected_icon, f"Failed for {url}")

    def test_audio_playlist_icons(self):
        item = {"url": "http://test", "status": "Queued", "is_audio": True}
        control = DownloadItemControl(item, MagicMock(), MagicMock(), MagicMock())
        icon_container = control.view.content.controls[0]
        self.assertEqual(icon_container.content.name, ft.Icons.AUDIO_FILE)

        item = {"url": "http://test", "status": "Queued", "is_playlist": True}
        control = DownloadItemControl(item, MagicMock(), MagicMock(), MagicMock())
        icon_container = control.view.content.controls[0]
        self.assertEqual(icon_container.content.name, ft.Icons.PLAYLIST_PLAY)

    def test_update_actions_logic(self):
        # Downloading state -> Cancel button
        item = {"url": "http://test", "status": "Downloading"}
        control = DownloadItemControl(item, MagicMock(), MagicMock(), MagicMock())
        actions = control.actions_row.controls
        # Should have Cancel
        self.assertTrue(
            any(
                isinstance(c, ft.IconButton) and c.icon == ft.Icons.CLOSE
                for c in actions
            )
        )

        # Error state -> Retry and Remove
        item = {"url": "http://test", "status": "Error"}
        control = DownloadItemControl(
            item, MagicMock(), MagicMock(), MagicMock(), on_retry=MagicMock()
        )
        actions = control.actions_row.controls
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

        # Queued state -> Reorder and Remove
        item = {"url": "http://test", "status": "Queued"}
        control = DownloadItemControl(item, MagicMock(), MagicMock(), MagicMock())
        actions = control.actions_row.controls
        # Reorder is a Column
        self.assertTrue(any(isinstance(c, ft.Column) for c in actions))
        self.assertTrue(
            any(
                isinstance(c, ft.IconButton) and c.icon == ft.Icons.DELETE_OUTLINE
                for c in actions
            )
        )

    def test_update_progress_logic(self):
        item = {"url": "http://test", "status": "Queued"}
        control = DownloadItemControl(item, MagicMock(), MagicMock(), MagicMock())

        # Mock update methods to avoid Flet errors (page not attached)
        control.status_text.update = MagicMock()
        control.details_text.update = MagicMock()
        control.progress_bar.update = MagicMock()
        control.title_text.update = MagicMock()
        control.actions_row.update = MagicMock()

        # Downloading
        item["status"] = "Downloading"
        item["speed"] = "1 MB/s"
        item["eta"] = "10s"
        control.update_progress()
        self.assertIn("1 MB/s", control.details_text.value)

        # Completed
        item["status"] = "Completed"
        control.update_progress()
        self.assertEqual(control.progress_bar.value, 1)

        # Error
        item["status"] = "Error"
        control.update_progress()
        self.assertEqual(control.progress_bar.value, 0)

        # Scheduled
        item["status"] = "Scheduled"
        control.update_progress()
        self.assertEqual(control.progress_bar.value, 0)

    def test_action_callbacks(self):
        # Test clicks trigger callbacks
        mock_cancel = MagicMock()
        mock_retry = MagicMock()
        mock_remove = MagicMock()
        mock_reorder = MagicMock()

        item = {"url": "http://test", "status": "Downloading"}
        control = DownloadItemControl(
            item, mock_cancel, mock_remove, mock_reorder, mock_retry
        )

        # Find cancel button
        cancel_btn = next(
            c for c in control.actions_row.controls if c.icon == ft.Icons.CLOSE
        )
        cancel_btn.on_click(None)
        mock_cancel.assert_called_with(item)

        # Switch to Error for Retry
        item["status"] = "Error"
        control._update_actions()
        retry_btn = next(
            c for c in control.actions_row.controls if c.icon == ft.Icons.REFRESH
        )
        retry_btn.on_click(None)
        mock_retry.assert_called_with(item)

        # Remove
        remove_btn = next(
            c for c in control.actions_row.controls if c.icon == ft.Icons.DELETE_OUTLINE
        )
        remove_btn.on_click(None)
        mock_remove.assert_called_with(item)

        # Queued for Reorder
        item["status"] = "Queued"
        control._update_actions()
        reorder_col = next(
            c for c in control.actions_row.controls if isinstance(c, ft.Column)
        )
        up_btn = reorder_col.controls[0]
        down_btn = reorder_col.controls[1]

        up_btn.on_click(None)
        mock_reorder.assert_called_with(item, -1)

        down_btn.on_click(None)
        mock_reorder.assert_called_with(item, 1)
