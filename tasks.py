"""
Background task processing module.

Handles the download queue, threading, and status updates.
Refactored for better modularity and error handling.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from app_state import state
from downloader.core import download_video

logger = logging.getLogger(__name__)

# Semaphore to limit concurrent downloads
MAX_CONCURRENT_DOWNLOADS = 3
_active_downloads = threading.Semaphore(MAX_CONCURRENT_DOWNLOADS)
_process_queue_lock = threading.RLock()


def process_queue():
    """
    Process items in the queue.
    Starts new downloads if slots are available.
    """
    if state.shutdown_flag.is_set():
        return

    # Log status (optional, debug only)
    try:
        # pylint: disable=protected-access
        active = MAX_CONCURRENT_DOWNLOADS - _active_downloads._value
        logger.debug("Process queue check. Active: %d/%d", active, MAX_CONCURRENT_DOWNLOADS)
    except ValueError:
        pass

    while True:
        if state.shutdown_flag.is_set():
            break

        # Check for slot
        if not _active_downloads.acquire(blocking=False):
            break

        # Get next item
        item = state.queue_manager.claim_next_downloadable()
        if not item:
            _active_downloads.release()
            break

        # Start thread
        try:
            t = threading.Thread(
                target=download_task,
                args=(item,),
                daemon=True,
                name=f"DL-{item['url'][:30]}"
            )
            t.start()
        except Exception as e:
            logger.error("Failed to start download thread: %s", e)
            item["status"] = "Error"
            _active_downloads.release()


def _update_progress_ui(item: Dict[str, Any]):
    """Helper to update UI control if present."""
    if "control" in item:
        try:
            item["control"].update_progress()
        except Exception:
            pass


def _progress_hook_factory(item: Dict[str, Any]):
    """Creates a closure for the progress hook."""
    def progress_hook(d):
        if state.shutdown_flag.is_set():
            raise InterruptedError("Shutdown initiated")

        if d["status"] == "downloading":
            p_str = d.get("_percent_str", "0%").replace("%", "")
            try:
                progress = float(p_str) / 100
            except ValueError:
                progress = 0

            item["progress"] = progress
            item["speed"] = d.get("_speed_str", "N/A")
            item["eta"] = d.get("_eta_str", "N/A")
            item["size"] = d.get("_total_bytes_str", "N/A")
            _update_progress_ui(item)

        elif d["status"] == "finished":
            item["progress"] = 1.0
            item["status"] = "Processing"
            _update_progress_ui(item)

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
    logger.info("Starting download: %s", url)

    try:
        item["status"] = "Downloading"
        _update_progress_ui(item)

        # Prepare hooks and execute
        phook = _progress_hook_factory(item)

        info = download_video(
            url=url,
            output_path=item.get("output_path", "."),
            video_format=item.get("video_format", "best"),
            progress_hook=phook,
            cancel_token=None,  # Logic for cancellation would go here
            playlist=item.get("playlist", False),
            sponsorblock=item.get("sponsorblock", False),
            use_aria2c=item.get("use_aria2c", False),
            gpu_accel=item.get("gpu_accel"),
            output_template=item.get("output_template", "%(title)s.%(ext)s"),
            start_time=item.get("start_time"),
            end_time=item.get("end_time"),
            force_generic=item.get("force_generic", False),
            cookies_from_browser=item.get("cookies_from_browser"),
        )

        # Success
        item["status"] = "Completed"
        item["filename"] = info.get("filename", "Unknown")
        item["progress"] = 1.0

        _log_to_history(item, info.get("filepath"))
        _update_progress_ui(item)

    except Exception as e:
        # Check for cancellation
        msg = str(e)
        if "Cancelled" in msg or item.get("status") == "Cancelled":
            logger.info("Download cancelled: %s", url)
            item["status"] = "Cancelled"
        else:
            logger.error("Download failed: %s", e, exc_info=True)
            item["status"] = "Error"
            item["error"] = str(e)

        _update_progress_ui(item)

    finally:
        _active_downloads.release()
        process_queue()
