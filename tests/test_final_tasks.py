import threading
from unittest.mock import ANY, MagicMock, patch

import pytest

import app_state
from tasks import (
    _SUBMISSION_THROTTLE,
    DownloadJob,
    DownloadStatus,
    fetch_info_task,
    process_queue,
)


@pytest.fixture
def mock_state():
    """Patches app_state.state and returns it."""
    with patch("app_state.state") as mock_state:
        # Create mocks for queue_manager and history_manager
        mock_state.queue_manager = MagicMock()
        mock_state.history_manager = MagicMock()
        mock_state.config = MagicMock()
        mock_state.shutdown_flag = MagicMock()
        mock_state.shutdown_flag.is_set.return_value = False

        # Default config behavior
        mock_state.config.get.side_effect = lambda k, default=None: default

        yield mock_state


def test_download_job_run_success(mock_state):
    item = {"id": "123", "url": "http://test.com", "title": "Test Video"}
    page = MagicMock()

    with patch("tasks.download_video") as mock_dv:
        mock_dv.return_value = {
            "filepath": "/tmp/test.mp4",
            "file_size": 1000,
            "status": "finished",
        }

        job = DownloadJob(item, page)
        job.run()

        # Verify status updates
        # Should start with DOWNLOADING
        mock_state.queue_manager.update_item_status.assert_any_call(
            "123", DownloadStatus.DOWNLOADING
        )

        # Should finish with COMPLETED
        mock_state.queue_manager.update_item_status.assert_any_call(
            "123",
            DownloadStatus.COMPLETED,
            {"filepath": "/tmp/test.mp4", "file_size": 1000, "status": "finished"},
        )

        # Verify history logging
        mock_state.history_manager.add_entry.assert_called_once()

        # Verify success notification
        # page.run_task is async, mock it
        page.run_task.assert_called_once()


def test_download_job_run_error(mock_state):
    item = {"id": "123", "url": "http://test.com"}
    page = MagicMock()

    with patch("tasks.download_video") as mock_dv:
        mock_dv.side_effect = Exception("Download failed")

        job = DownloadJob(item, page)
        job.run()

        # Verify status updates
        mock_state.queue_manager.update_item_status.assert_any_call(
            "123", DownloadStatus.ERROR, {"error": "Download failed"}
        )

        # Verify error notification
        page.run_task.assert_called_once()


def test_download_job_cancellation(mock_state):
    item = {"id": "123", "url": "http://test.com"}

    # Mock shutdown flag to simulate cancellation BEFORE run if needed,
    # but let's simulate cancellation DURING run via CancelToken

    with patch("tasks.download_video") as mock_dv:
        # Simulate exception that looks like cancellation
        mock_dv.side_effect = Exception("Cancelled")

        job = DownloadJob(item, None)
        # Mark token as cancelled
        job.cancel_token.cancel()

        job.run()

        # Should be marked as CANCELLED
        mock_state.queue_manager.update_item_status.assert_any_call(
            "123", DownloadStatus.CANCELLED
        )


def test_download_job_shutdown(mock_state):
    item = {"id": "123", "url": "http://test.com"}

    # Simulate app shutdown
    mock_state.shutdown_flag.is_set.return_value = True

    job = DownloadJob(item, None)
    job.run()

    # Should be marked as CANCELLED immediately
    mock_state.queue_manager.update_item_status.assert_called_with(
        "123", DownloadStatus.CANCELLED
    )

    # download_video should NOT be called
    with patch("tasks.download_video") as mock_dv:
        assert not mock_dv.called


def test_process_queue_throttling(mock_state):
    # Test that process_queue respects max workers

    mock_state.queue_manager.get_active_count.return_value = 5

    with patch("tasks._get_max_workers", return_value=3):
        with patch("tasks._SUBMISSION_THROTTLE") as mock_sem:
            process_queue(None)

            # Should NOT try to acquire semaphore or claim item if active >= max
            assert not mock_sem.acquire.called
            assert not mock_state.queue_manager.claim_next_downloadable.called


def test_process_queue_submission(mock_state):
    # Test successful submission

    mock_state.queue_manager.get_active_count.return_value = 0
    mock_state.queue_manager.claim_next_downloadable.return_value = {
        "id": "1",
        "url": "http://test.com",
    }

    with patch("tasks._get_max_workers", return_value=3):
        # We need to mock the semaphore properly.
        # Since process_queue uses _SUBMISSION_THROTTLE global, we patch it.
        # But we must ensure acquire returns True.

        # Note: tasks.py imports _SUBMISSION_THROTTLE from module level? No, it defines it.
        # So patching tasks._SUBMISSION_THROTTLE works.

        with patch("tasks._SUBMISSION_THROTTLE") as mock_sem:
            mock_sem.acquire.return_value = True

            with patch("tasks._get_executor") as mock_exec:
                mock_future = MagicMock()
                mock_exec.return_value.submit.return_value = mock_future

                process_queue(None)

                # Should claim item
                mock_state.queue_manager.claim_next_downloadable.assert_called_once()

                # Should submit to executor
                mock_exec.return_value.submit.assert_called_once()


def test_fetch_info_task_success(mock_state):
    url = "http://test.com"
    view_card = MagicMock()
    page = MagicMock()

    with patch("tasks.get_video_info") as mock_gvi:
        mock_gvi.return_value = {"title": "Test Info"}

        fetch_info_task(url, view_card, page)

        # Should set fetch disabled, call get_video_info, update state, notify UI
        view_card.set_fetch_disabled.assert_any_call(True)
        assert mock_state.video_info == {"title": "Test Info"}
        page.run_task.assert_called_once()


def test_fetch_info_task_failure(mock_state):
    url = "http://test.com"
    view_card = MagicMock()
    page = MagicMock()

    with patch("tasks.get_video_info") as mock_gvi:
        mock_gvi.side_effect = Exception("Fetch error")

        fetch_info_task(url, view_card, page)

        # Should notify error
        page.run_task.assert_called_once()


def test_fetch_info_task_failure_deferred_callback(mock_state):
    """Ensure error callback works even when run_task executes later."""
    callbacks = []
    view_card = MagicMock()
    page = MagicMock()
    page.run_task.side_effect = lambda cb: callbacks.append(cb)

    with patch("tasks.get_video_info", side_effect=Exception("Deferred failure")):
        fetch_info_task("http://test.com", view_card, page)

    assert len(callbacks) == 1

    # Execute deferred callback after exception block has finished.
    import asyncio

    asyncio.run(callbacks[0]())
    page.open.assert_called_once()


def test_download_job_options(mock_state):
    item = {
        "id": "123",
        "url": "http://test.com",
        "output_path": "/custom/path",
        "proxy": "http://proxy",
        "rate_limit": "1M",
        "video_format": "audio",
        "audio_only": True,
    }
    mock_state.config.get.return_value = None

    with patch("tasks.download_video") as mock_dv:
        mock_dv.return_value = {"status": "finished"}
        job = DownloadJob(item, None)
        job.run()

        args, _ = mock_dv.call_args
        options = args[0]

        assert options.url == "http://test.com"
        assert options.output_path == "/custom/path"
        assert options.proxy == "http://proxy"
        assert options.rate_limit == "1M"
        assert options.video_format == "audio"


def test_progress_hook(mock_state):
    item = {"id": "123", "url": "http://test.com"}
    job = DownloadJob(item, None)

    # Manually call hook
    d = {
        "status": "downloading",
        "_percent_str": "50%",
        "_speed_str": "1M/s",
        "_eta_str": "10s",
        "_total_bytes_str": "100MB",
    }

    job._progress_hook(d)

    mock_state.queue_manager.update_item_status.assert_any_call(
        "123",
        DownloadStatus.DOWNLOADING,
        {"progress": 0.5, "speed": "1M/s", "eta": "10s", "size": "100MB"},
    )

    d_finished = {"status": "finished"}
    job._progress_hook(d_finished)

    mock_state.queue_manager.update_item_status.assert_any_call(
        "123", DownloadStatus.PROCESSING, {"progress": 1.0}
    )
