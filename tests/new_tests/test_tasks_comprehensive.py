import pytest
from unittest.mock import MagicMock, patch, ANY
import threading
from tasks import DownloadJob, process_queue, _SUBMISSION_THROTTLE
from downloader.types import DownloadStatus


@pytest.fixture
def mock_app_state():
    with patch("tasks.app_state") as mock_state:
        # Setup QueueManager
        mock_qm = MagicMock()
        mock_state.state.queue_manager = mock_qm

        # Setup Config
        mock_state.state.config = {
            "download_path": "/tmp/downloads",
            "proxy": None,
            "rate_limit": None,
            "cookies": None,
            "output_template": "%(title)s.%(ext)s",
        }

        # Setup shutdown flag
        mock_state.state.shutdown_flag = MagicMock()
        mock_state.state.shutdown_flag.is_set.return_value = False

        yield mock_state


@pytest.fixture
def mock_download_video():
    with patch("tasks.download_video") as mock_dv:
        yield mock_dv


def test_download_job_success(mock_app_state, mock_download_video):
    item = {"id": "123", "url": "http://example.com/video", "title": "Test Video"}
    page = MagicMock()

    # Mock successful download
    mock_download_video.return_value = {"filename": "video.mp4"}

    job = DownloadJob(item, page)
    job.run()

    # Verify status updates
    qm = mock_app_state.state.queue_manager
    qm.register_cancel_token.assert_called_once()
    qm.update_item_status.assert_any_call("123", DownloadStatus.DOWNLOADING)
    qm.update_item_status.assert_any_call(
        "123", DownloadStatus.COMPLETED, {"filename": "video.mp4"}
    )
    qm.unregister_cancel_token.assert_called_once()


def test_download_job_failure(mock_app_state, mock_download_video):
    item = {"id": "123", "url": "http://fail.com"}
    page = MagicMock()

    mock_download_video.side_effect = Exception("Network Error")

    job = DownloadJob(item, page)
    job.run()

    qm = mock_app_state.state.queue_manager
    qm.update_item_status.assert_any_call(
        "123", DownloadStatus.ERROR, {"error": "Network Error"}
    )


def test_download_job_cancellation_during_run(mock_app_state, mock_download_video):
    item = {"id": "123", "url": "http://cancel.com"}

    # Simulate cancellation during download
    mock_download_video.side_effect = Exception("Cancelled")

    job = DownloadJob(item, None)
    job.run()

    qm = mock_app_state.state.queue_manager
    qm.update_item_status.assert_any_call("123", DownloadStatus.CANCELLED)


def test_process_queue_throttling(mock_app_state):
    # Mock semaphore to be full
    with patch("tasks._SUBMISSION_THROTTLE") as mock_sem:
        mock_sem.acquire.return_value = False
        mock_app_state.state.queue_manager.get_active_count.return_value = 0

        process_queue(None)

        # Should not claim next item if semaphore full
        mock_app_state.state.queue_manager.claim_next_downloadable.assert_not_called()


def test_process_queue_submission(mock_app_state):
    item = {"id": "123", "url": "http://go.com"}
    mock_app_state.state.queue_manager.claim_next_downloadable.return_value = item
    mock_app_state.state.queue_manager.get_active_count.return_value = 0

    # We need to mock _get_max_workers to ensure we don't hit the limit check
    with (
        patch("tasks._get_max_workers", return_value=5),
        patch("tasks._get_executor") as mock_exec,
    ):
        process_queue(None)

        mock_exec().submit.assert_called_once()


def test_process_queue_max_workers_limit(mock_app_state):
    mock_app_state.state.queue_manager.get_active_count.return_value = 5
    with patch("tasks._get_max_workers", return_value=3):
        process_queue(None)
        # Should return early
        mock_app_state.state.queue_manager.claim_next_downloadable.assert_not_called()
