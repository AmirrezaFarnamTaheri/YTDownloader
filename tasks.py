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
from utils import CancelToken

logger = logging.getLogger(__name__)

# Executor for managing download threads
MAX_WORKERS = 3
_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="DLWorker")
_active_count = 0
_active_count_lock = threading.Lock()

def process_queue():
    """
    Process items in the queue.
    Submits new downloads to the executor if slots are available.
    """
    global _active_count

    if state.shutdown_flag.is_set():
        return

    while True:
        if state.shutdown_flag.is_set():
            break

        # Atomically check capacity and claim an item
        with _active_count_lock:
            if _active_count >= MAX_WORKERS:
                break

            item = state.queue_manager.claim_next_downloadable()
            if not item:
                break

            _active_count += 1

        # Submit to executor
        try:
            _executor.submit(download_task, item)
        except Exception as e:
            logger.error("Failed to submit task: %s", e)
            with _active_count_lock:
                _active_count -= 1

            # Use atomic update
            state.queue_manager.update_item_status(
                 item.get("id"),
                 "Error",
                 {"error": "Failed to start"}
            )


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

        # Check cancellation frequently
        if cancel_token.cancelled:
            raise InterruptedError("Download Cancelled by user")

        status = d.get("status")

        if status == "downloading":
            p_str = d.get("_percent_str", "0%").replace("%", "")
            try:
                progress = float(p_str) / 100
            except (ValueError, TypeError):
                progress = 0

            # Atomic-ish local update (UI reads from this dict reference)
            item["progress"] = progress
            item["speed"] = d.get("_speed_str", "N/A")
            item["eta"] = d.get("_eta_str", "N/A")
            item["size"] = d.get("_total_bytes_str", "N/A")
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
    global _active_count

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

        info = download_video(
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

        # Success
        state.queue_manager.update_item_status(
            item_id,
            "Completed",
            {
                "filename": info.get("filename", "Unknown"),
                "progress": 1.0
            }
        )
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
        else:
            logger.error("Download failed: %s", e, exc_info=True)
            state.queue_manager.update_item_status(
                item_id,
                "Error",
                {"error": str(e)}
            )

        _update_progress_ui(item)

    finally:
        # Cleanup
        if item_id:
            state.queue_manager.unregister_cancel_token(item_id)

        with _active_count_lock:
            _active_count -= 1

        # Trigger next check in main loop
        # We need to wake up the background loop in main.py to process more items
        try:
             # Use the public condition variable (must acquire lock)
             with state.queue_manager._has_work:
                 state.queue_manager._has_work.notify_all()
        except Exception:
            pass
