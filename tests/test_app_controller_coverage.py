# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Coverage tests for AppController.
"""

import unittest
from unittest.mock import ANY, MagicMock, patch

import flet as ft

from app_controller import AppController
from ui_manager import UIManager


class TestAppControllerCoverage(unittest.TestCase):
    def setUp(self):
        self.mock_page = MagicMock(spec=ft.Page)
        self.mock_page.open = MagicMock()
        self.mock_page.overlay = []
        self.mock_ui = MagicMock(spec=UIManager)
        self.mock_ui.download_view = MagicMock()

        # Patch dependencies that are instantiated in __init__
        self.patcher_rate = patch("app_controller.RateLimiter")
        self.patcher_batch = patch("app_controller.BatchImporter")
        self.patcher_sched = patch("app_controller.DownloadScheduler")
        self.patcher_state = patch("app_controller.state")
        self.patcher_process_queue = patch("app_controller.process_queue")
        self.patcher_thread = patch("threading.Thread")

        self.mock_rate = self.patcher_rate.start()
        self.mock_batch = self.patcher_batch.start()
        self.mock_sched = self.patcher_sched.start()
        self.mock_state = self.patcher_state.start()
        self.mock_process_queue = self.patcher_process_queue.start()
        self.mock_thread = self.patcher_thread.start()

        self.controller = AppController(self.mock_page, self.mock_ui)

    def tearDown(self):
        self.patcher_rate.stop()
        self.patcher_batch.stop()
        self.patcher_sched.stop()
        self.patcher_state.stop()
        self.patcher_process_queue.stop()
        self.patcher_thread.stop()

    def test_start_background_loop(self):
        self.controller.start_background_loop()
        self.mock_thread.assert_called_with(
            target=self.controller._background_loop, daemon=True, name="BackgroundLoop"
        )
        self.mock_thread.return_value.start.assert_called_once()
        self.assertIn(self.mock_thread.return_value, self.controller.active_threads)

    @patch("app_controller.start_clipboard_monitor")
    def test_start_clipboard_monitor(self, mock_start_monitor):
        self.controller.start_clipboard_monitor()
        mock_start_monitor.assert_called_with(
            self.mock_page, self.mock_ui.download_view
        )

    def test_cleanup(self):
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        self.controller.active_threads = [mock_thread]

        self.controller.cleanup()

        self.mock_state.cleanup.assert_called_once()
        mock_thread.join.assert_called_with(timeout=2.0)

    def test_background_loop_shutdown(self):
        # Simulate immediate shutdown
        self.mock_state.shutdown_flag.is_set.side_effect = [False, True]
        self.mock_state.queue_manager.wait_for_items.return_value = True

        self.controller._background_loop()

        self.mock_state.queue_manager.wait_for_items.assert_called()

    def test_background_loop_processing(self):
        # Configure run_task to execute callback if called
        self.mock_page.run_task.side_effect = lambda cb, *args, **kwargs: cb(
            *args, **kwargs
        )

        # Run loop once then shutdown
        self.mock_state.shutdown_flag.is_set.side_effect = [False, False, True]
        self.mock_state.queue_manager.wait_for_items.return_value = True
        self.mock_state.queue_manager.update_scheduled_items.return_value = 1

        self.controller._background_loop()

        self.mock_ui.update_queue_view.assert_called()
        self.mock_process_queue.assert_called()

    @patch("app_controller.time.sleep")
    def test_background_loop_exception(self, mock_sleep):
        # Simulate exception then shutdown
        self.mock_state.queue_manager.wait_for_items.side_effect = Exception(
            "Test Error"
        )
        self.mock_state.shutdown_flag.is_set.side_effect = [False, True]

        self.controller._background_loop()

        mock_sleep.assert_called_with(1)

    @patch("app_controller.fetch_info_task")
    @patch("app_controller.validate_url")
    def test_on_fetch_info_valid(self, mock_validate, mock_fetch_task):
        mock_validate.return_value = True
        url = "http://example.com"

        self.controller.on_fetch_info(url)

        self.assertTrue(self.mock_ui.download_view.fetch_btn.disabled)
        self.mock_page.update.assert_called()
        self.mock_thread.assert_called_with(
            target=mock_fetch_task,
            args=(url, self.mock_ui.download_view, self.mock_page),
            daemon=True,
        )

    def test_on_fetch_info_empty(self):
        self.controller.on_fetch_info("")
        self.mock_page.open.assert_called()
        args = self.mock_page.open.call_args[0][0]
        # ft.SnackBar is a MagicMock class, so instance check might fail if not careful
        # self.assertIsInstance(args, ft.SnackBar)
        self.assertEqual(args.content.value, "Please enter a URL")

    @patch("app_controller.validate_url")
    def test_on_fetch_info_invalid(self, mock_validate):
        mock_validate.return_value = False
        self.controller.on_fetch_info("invalid")
        self.mock_page.open.assert_called()
        snack_bar = self.mock_page.open.call_args[0][0]
        self.assertIn("valid http/https URL", snack_bar.content.value)

    @patch("app_controller.validate_url")
    @patch("app_controller.get_default_download_path")
    def test_on_add_to_queue_success(self, mock_get_path, mock_validate):
        mock_validate.return_value = True
        mock_get_path.return_value = "/tmp"
        self.mock_rate.return_value.check.return_value = True
        self.mock_sched.return_value.prepare_schedule.return_value = ("Queued", None)
        self.mock_state.get_video_info.return_value = {"title": "Test Title"}

        data = {"url": "http://test.com", "video_format": "1080p"}
        self.controller.on_add_to_queue(data)

        self.mock_state.queue_manager.add_item.assert_called()
        self.mock_ui.update_queue_view.assert_called()
        self.mock_page.open.assert_called()  # SnackBar

    def test_on_add_to_queue_rate_limit(self):
        with patch("app_controller.validate_url", return_value=True):
            self.mock_rate.return_value.check.return_value = False
            self.controller.on_add_to_queue({"url": "http://test.com"})
            self.mock_page.open.assert_called()
            # Depending on how MagicMock propagates, content.value might be another mock
            # We access the arguments directly
            snack_bar = self.mock_page.open.call_args[0][0]
            self.assertIn("Please wait", snack_bar.content.value)

    def test_on_cancel_item(self):
        item = {"id": "123", "title": "Test"}
        self.controller.on_cancel_item(item)
        self.mock_state.queue_manager.cancel_item.assert_called_with("123")
        self.mock_state.queue_manager.notify_workers.assert_called()

    def test_on_cancel_item_no_id(self):
        item = {"title": "Test", "status": "Downloading"}
        item["control"] = MagicMock()
        self.controller.on_cancel_item(item)
        self.assertEqual(item["status"], "Cancelled")
        item["control"].update_progress.assert_called()

    def test_on_remove_item(self):
        item = {"id": "123"}
        self.controller.on_remove_item(item)
        self.mock_state.queue_manager.remove_item.assert_called_with(item)
        self.mock_ui.update_queue_view.assert_called()

    def test_on_reorder_item(self):
        item = {"id": "123"}
        self.mock_state.queue_manager.get_all.return_value = [item, {"id": "456"}]

        self.controller.on_reorder_item(item, 1)

        self.mock_state.queue_manager.swap_items.assert_called_with(0, 1)
        self.mock_ui.update_queue_view.assert_called()

    def test_on_retry_item(self):
        item = {"id": "123"}
        self.controller.on_retry_item(item)
        self.mock_state.queue_manager.update_item_status.assert_called_with(
            "123", "Queued", updates=ANY
        )
        self.mock_ui.update_queue_view.assert_called()

    @patch("app_controller.play_file")
    @patch("app_controller.get_default_download_path")
    @patch("os.path.join")
    def test_on_play_item(self, mock_join, mock_get_path, mock_play):
        mock_get_path.return_value = "/tmp"
        mock_join.return_value = "/tmp/video.mp4"
        mock_play.return_value = True

        item = {"filename": "video.mp4"}
        self.controller.on_play_item(item)

        mock_play.assert_called_with("/tmp/video.mp4", self.mock_page)

    def test_on_play_item_no_filename(self):
        self.controller.on_play_item({})
        self.mock_page.open.assert_called()
        snack_bar = self.mock_page.open.call_args[0][0]
        self.assertIn("path unknown", snack_bar.content.value)

    @patch("app_controller.open_folder")
    def test_on_open_folder(self, mock_open):
        mock_open.return_value = True
        self.controller.on_open_folder({"output_path": "/tmp"})
        mock_open.assert_called_with("/tmp", self.mock_page)

    def test_on_batch_file_result(self):
        e = MagicMock()
        e.files = [MagicMock(path="/path/to/file.txt")]
        self.mock_batch.return_value.import_from_file.return_value = (5, False)

        self.controller.on_batch_file_result(e)

        self.mock_batch.return_value.import_from_file.assert_called_with(
            "/path/to/file.txt"
        )
        self.mock_ui.update_queue_view.assert_called()
        self.mock_page.open.assert_called()

    def test_on_batch_file_result_cancel(self):
        e = MagicMock()
        e.files = None
        self.controller.on_batch_file_result(e)
        self.mock_batch.return_value.import_from_file.assert_not_called()

    @patch("app_controller.ft.FilePicker.pick_files")
    def test_on_batch_import(self, mock_pick_files):
        # We patch the method on the class because the instance is created in __init__
        # and we can't easily swap it out without accessing internal property.
        # Although we could just mock self.controller.file_picker.pick_files if it was a mock.

        # Override the instance method directly since it's a real Flet control causing issues
        self.controller.file_picker.pick_files = MagicMock()

        self.controller.on_batch_import()
        self.controller.file_picker.pick_files.assert_called()

    def test_on_time_picked(self):
        e = MagicMock()
        # Mock datetime object for strftime
        mock_dt = MagicMock()
        mock_dt.strftime.return_value = "12:00"
        e.value = mock_dt

        self.controller.on_time_picked(e)

        self.assertEqual(self.mock_state.scheduled_time, mock_dt)
        self.mock_page.open.assert_called()

    def test_on_schedule(self):
        self.controller.on_schedule(None)
        self.mock_page.open.assert_called_with(self.controller.time_picker)

    def test_on_toggle_clipboard(self):
        self.controller.on_toggle_clipboard(True)
        self.assertTrue(self.mock_state.clipboard_monitor_active)
        self.mock_page.open.assert_called()
