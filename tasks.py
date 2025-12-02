"""
Background task processing module.

Handles the download queue, threading, and status updates.
Refactored to use ThreadPoolExecutor and per-task CancelTokens.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from app_state import state
from downloader.core import download_video
from downloader.types import DownloadOptions
from utils import CancelToken

logger = logging.getLogger(__name__)

# Executor for managing download threads
MAX_WORKERS = 3
_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="DLWorker")
_active_count = 0
_active_count_lock = threading.Lock()

# Throttle submission to executor to avoid flooding it with "Allocating" tasks
# that sit in the executor queue and can't be easily cancelled.
# We limit the number of submitted-but-not-finished tasks to MAX_WORKERS.
_submission_throttle = threading.Semaphore(MAX_WORKERS)
# And lock
_process_queue_lock = threading.RLock()

# Compatibility alias for tests (legacy)
_active_downloads = _submission_throttle


def process_queue():
    """
    Process items in the queue.
    Submits new downloads to the executor if slots are available.
    """
    global _active_count

    if state.shutdown_flag.is_set():
        return

    with _process_queue_lock:
        while True:
            if state.shutdown_flag.is_set():
                break

            # Use semaphore for limiting
            if not _submission_throttle.acquire(blocking=False):
                break

            # Claim item
            item = state.queue_manager.claim_next_downloadable()
            if not item:
                _submission_throttle.release()
                break

            with _active_count_lock:
                _active_count += 1

            # Submit to executor
            try:
                # We submit a wrapper that releases semaphore when done
                _executor.submit(_wrapped_download_task, item)
            except Exception as e:
                logger.error("Failed to submit task: %s", e)
                with _active_count_lock:
                    _active_count -= 1
                _submission_throttle.release()

                state.queue_manager.update_item_status(
                     item.get("id"),
                     "Error",
                     {"error": "Failed to start"}
                )


def _wrapped_download_task(item):
    """Wrapper to ensure semaphore release."""
    try:
        download_task(item)
    finally:
        _submission_throttle.release()
        with _active_count_lock:
            _active_count -= 1

        # Notify
        try:
             with state.queue_manager._has_work:
                 state.queue_manager._has_work.notify_all()
        except Exception:
            pass


def _update_progress_ui(item: Dict[str, Any]):
    """Helper to update UI control if present."""
    if "control" in item:
        try:
            item["control"].update_progress()
        except Exception:
            pass


def _progress_hook_factory(item: Dict[str, Any], cancel_token: CancelToken):
    """Creates a closure for the progress hook."""
    def progress_hook(d):
        if state.shutdown_flag.is_set():
            raise InterruptedError("Shutdown initiated")

        # Check cancellation and pause state via token check
        cancel_token.check()

        status = d.get("status")

        if status == "downloading":
            p_raw = d.get("_percent_str", "0%")
            # Defensive coding
            if not isinstance(p_raw, str):
                p_raw = "0%"

            p_str = p_raw.replace("%", "")
            try:
                progress = float(p_str) / 100.0
            except (ValueError, TypeError):
                progress = 0.0

            # Atomic-ish local update (UI reads from this dict reference)
            item["progress"] = progress
            item["speed"] = d.get("_speed_str", "") or "N/A"
            item["eta"] = d.get("_eta_str", "") or "N/A"
            item["size"] = d.get("_total_bytes_str", "") or "N/A"
            _update_progress_ui(item)

        elif status == "finished":
            item["progress"] = 1.0
            item["status"] = "Processing"
            _update_progress_ui(item)

        else:
             # Ignore other statuses or unknown
             pass

    return progress_hook


def _log_to_history(item: Dict[str, Any], filepath: str):
    """Log completed download to history safely."""
    try:
        from history_manager import HistoryManager
        HistoryManager.add_entry(
            item["url"],
            item.get("title", item["url"]),
            item.get("output_path", "."),
            item.get("video_format", "best"),
            "Completed",
            item.get("size", "Unknown"),
            filepath,
        )
    except Exception as e:
        logger.error("Failed to add to history: %s", e)


def download_task(item: Dict[str, Any]):
    """
    Worker function for a single download.
    Executes the download, updates status, and logs to history.
    """
    url = item["url"]
    item_id = item.get("id")

    # Create and register CancelToken
    cancel_token = CancelToken()
    if item_id:
        state.queue_manager.register_cancel_token(item_id, cancel_token)

    logger.info("Starting download task: %s", url)

    try:
        state.queue_manager.update_item_status(item_id, "Downloading")
        _update_progress_ui(item)

        # Prepare hooks and execute
        phook = _progress_hook_factory(item, cancel_token)

        # Map dict item to DownloadOptions
        options = DownloadOptions(
            url=url,
            output_path=item.get("output_path", "."),
            video_format=item.get("video_format", "best"),
            progress_hook=phook,
            cancel_token=cancel_token,
            playlist=item.get("playlist", False),
            sponsorblock=item.get("sponsorblock", False),
            use_aria2c=item.get("use_aria2c", False),
            gpu_accel=item.get("gpu_accel"),
            output_template=item.get("output_template", "%(title)s.%(ext)s"),
            start_time=item.get("start_time"),
            end_time=item.get("end_time"),
            force_generic=item.get("force_generic", False),
            cookies_from_browser=item.get("cookies_from_browser"),
            download_item=item # Pass item for advanced callbacks/debugging
        )

        info = download_video(options)

        # Success
        state.queue_manager.update_item_status(
            item_id,
            "Completed",
            {
                "filename": info.get("filename", "Unknown"),
                "progress": 1.0
            }
        )
        # Update the item dict in place because download_task caller might hold reference
        # But queue manager update_item_status does it for the queue.
        item["status"] = "Completed" # Update local ref for test assertion if test uses this ref

        _log_to_history(item, info.get("filepath"))
        _update_progress_ui(item)

    except Exception as e:
        # Check for cancellation
        msg = str(e)
        if "Cancelled" in msg or item.get("status") == "Cancelled" or cancel_token.cancelled:
            logger.info("Download cancelled: %s", url)

            # Ensure status is definitely cancelled and reset progress
            state.queue_manager.update_item_status(
                item_id,
                "Cancelled",
                {
                    "progress": 0,
                    "speed": "",
                    "eta": "",
                    "size": ""
                }
            )
            item["status"] = "Cancelled" # Update local ref
        else:
            logger.error("Download failed: %s", e, exc_info=True)
            state.queue_manager.update_item_status(
                item_id,
                "Error",
                {"error": str(e)}
            )
            item["status"] = "Error" # Update local ref

        _update_progress_ui(item)

    finally:
        # Cleanup
        if item_id:
            state.queue_manager.unregister_cancel_token(item_id)
