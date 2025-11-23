import pytest
from unittest.mock import MagicMock, patch, ANY
import main
import flet as ft
from datetime import datetime, time

class TestMainCoverage:
    @pytest.fixture
    def mock_page(self):
        page = MagicMock(spec=ft.Page)
        page.overlay = []
        return page

    @pytest.fixture
    def mock_dependencies(self):
        # Patch objects IN main.py namespace because they are imported with 'from ... import ...'
        with patch("main.state") as mock_state, \
             patch("main.AppLayout") as MockLayout, \
             patch("main.start_clipboard_monitor"), \
             patch("main.process_queue"), \
             patch("main.threading.Thread"), \
             patch("main.fetch_info_task"), \
             patch("main.DownloadView"), \
             patch("main.QueueView"), \
             patch("main.HistoryView"), \
             patch("main.DashboardView"), \
             patch("main.RSSView"), \
             patch("main.SettingsView"), \
             patch("main.ft.FilePicker"), \
             patch("main.ft.TimePicker"):

            # Setup State
            state = mock_state
            state.queue_manager = MagicMock()
            state.config = {}
            state.video_info = {"title": "Test Title"}
            state.scheduled_time = None

            yield

    def test_main_initialization(self, mock_page, mock_dependencies):
        main.main(mock_page)

        assert mock_page.title == "StreamCatch - Ultimate Downloader"
        assert mock_page.add.called
        assert len(mock_page.overlay) == 2 # Pickers

    def test_on_fetch_info(self, mock_page, mock_dependencies):
        main.main(mock_page)
        # Capture the callback passed to DownloadView
        # DownloadView(on_fetch_info, ...)
        args = main.DownloadView.call_args[0]
        on_fetch_info = args[0]

        # Test empty URL
        on_fetch_info("")
        mock_page.show_snack_bar.assert_called()

        # Test valid URL
        on_fetch_info("http://test.com")
        # Should start thread
        main.threading.Thread.assert_called()

    def test_on_add_to_queue(self, mock_page, mock_dependencies):
        main.main(mock_page)
        args = main.DownloadView.call_args[0]
        on_add_to_queue = args[1]

        data = {
            "url": "http://test.com",
            "video_format": "best",
            "playlist": False,
            "sponsorblock": False,
            "output_template": "%(title)s",
            "start_time": None,
            "end_time": None,
            "force_generic": False
        }

        # Test basic add
        main.download_view.url_input.value = "http://test.com"
        on_add_to_queue(data)
        main.state.queue_manager.add_item.assert_called()
        main.process_queue.assert_called()

        # Test scheduled
        main.state.scheduled_time = time(12, 0)
        on_add_to_queue(data)
        # Verify item has scheduled_time
        call_args = main.state.queue_manager.add_item.call_args[0][0]
        assert call_args["scheduled_time"] is not None

    def test_queue_callbacks(self, mock_page, mock_dependencies):
        main.main(mock_page)
        args = main.QueueView.call_args[0]
        on_cancel = args[1]
        on_remove = args[2]
        on_reorder = args[3]

        item = {"status": "Downloading", "url": "u"}
        main.state.current_download_item = item
        main.state.cancel_token = MagicMock()

        # Cancel
        on_cancel(item)
        assert item["status"] == "Cancelled"
        main.state.cancel_token.cancel.assert_called()

        # Remove
        on_remove(item)
        main.state.queue_manager.remove_item.assert_called_with(item)

        # Reorder
        main.state.queue_manager.get_all.return_value = [item, {"url": "u2"}]
        on_reorder(item, 1)
        main.state.queue_manager.swap_items.assert_called()

    def test_batch_import(self, mock_page, mock_dependencies):
        with patch("builtins.open", new_callable=MagicMock) as mock_open:
             mock_file = MagicMock()
             mock_file.__iter__.return_value = ["http://u1.com", "http://u2.com"]
             mock_open.return_value.__enter__.return_value = mock_file

             main.main(mock_page)

             mock_picker = main.ft.FilePicker.return_value
             on_result = mock_picker.on_result

             event = MagicMock()
             event.files = [MagicMock(path="test.txt")]

             on_result(event)

             assert main.state.queue_manager.add_item.call_count == 2

    def test_scheduling(self, mock_page, mock_dependencies):
        main.main(mock_page)
        mock_picker = main.ft.TimePicker.return_value
        on_change = mock_picker.on_change

        e = MagicMock()
        e.value = time(10, 0)
        on_change(e)

        assert main.state.scheduled_time == time(10, 0)

    def test_navigate(self, mock_page, mock_dependencies):
        main.main(mock_page)
        # AppLayout(..., navigate_to, ...)
        args = main.AppLayout.call_args[0]
        navigate_to = args[1]

        # Navigate to History (index 2)
        navigate_to(2)
        main.HistoryView.return_value.load.assert_called()

        # Navigate to Dashboard (index 3)
        navigate_to(3)
        main.DashboardView.return_value.load.assert_called()

    def test_retry_item(self, mock_page, mock_dependencies):
        main.main(mock_page)
        # queue_view.on_retry = on_retry_item
        # Access via main.queue_view.on_retry assignment
        # But queue_view is a Mock. logic assigns on_retry attribute.

        on_retry = main.queue_view.on_retry

        item = {"status": "Error"}
        on_retry(item)
        assert item["status"] == "Queued"
        main.process_queue.assert_called()

    def test_toggle_clipboard(self, mock_page, mock_dependencies):
        main.main(mock_page)
        # AppLayout(..., on_toggle_clipboard, ...)
        args = main.AppLayout.call_args[0]
        on_toggle = args[2]

        on_toggle(True)
        mock_page.show_snack_bar.assert_called()
        assert main.state.clipboard_monitor_active is True

        on_toggle(False)
        assert main.state.clipboard_monitor_active is False

    def test_batch_import_trigger(self, mock_page, mock_dependencies):
        main.main(mock_page)
        args = main.DownloadView.call_args[0]
        on_import = args[2]

        on_import()
        main.ft.FilePicker.return_value.pick_files.assert_called()

    def test_background_loop_exception(self, mock_page, mock_dependencies):
        # Patch Event to control the loop
        with patch("main.threading.Event") as mock_event_cls:
            mock_event = mock_event_cls.return_value
            # is_set called in loop: while not shutdown_flag.is_set()
            # We want: False (run once), True (stop)
            mock_event.is_set.side_effect = [False, True]

            main.main(mock_page)

            # Get background_loop from Thread call
            # main.threading.Thread was patched in fixture, but we access it via main.threading
            # mock_dependencies patches main.threading.Thread

            # Find the call that started background_loop
            # It's the one called inside main()
            # main.threading.Thread(target=background_loop, daemon=True).start()

            thread_mock = main.threading.Thread
            call_args = thread_mock.call_args
            target = call_args[1].get("target") if call_args else None
            if not target and call_args:
                 target = call_args[0][0]

            assert target is not None

            # Mock process_queue to raise exception
            main.process_queue.side_effect = Exception("Loop Error")

            with patch("time.sleep"):
                target() # Run loop logic
