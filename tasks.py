"""
Background task processing module.

Handles the download queue, threading, and status updates.
Refactored to use ThreadPoolExecutor and per-task CancelTokens.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from app_state import state
from downloader.core import download_video
from downloader.types import DownloadOptions
from utils import CancelToken

# Import HistoryManager at toplevel (assuming safe from circular deps if handled carefully,
# otherwise keep local import but suppress warning if absolutely necessary)
# Given previous lint output, it complained about import outside toplevel.
# Let's try top-level import. If circular, we might need a different structure,
# but history_manager usually doesn't import tasks.
try:
    from history_manager import HistoryManager
except ImportError:
    HistoryManager = None  # type: ignore

logger = logging.getLogger(__name__)

# Executor for managing download threads
MAX_WORKERS = 3
EXECUTOR = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="DLWorker")
_ACTIVE_COUNT = 0
_ACTIVE_COUNT_LOCK = threading.Lock()

# Throttle submission to executor to avoid flooding it with "Allocating" tasks
# that sit in the executor queue and can't be easily cancelled.
# We limit the number of submitted-but-not-finished tasks to MAX_WORKERS.
_SUBMISSION_THROTTLE = threading.Semaphore(MAX_WORKERS)
# And lock
_PROCESS_QUEUE_LOCK = threading.RLock()

# Compatibility alias for tests (legacy)
_active_downloads = _SUBMISSION_THROTTLE


def process_queue():
    """
    Process items in the queue.
    Submits new downloads to the executor if slots are available.
    """
    # pylint: disable=global-statement
    global _ACTIVE_COUNT

    if state.shutdown_flag.is_set():
        return

    with _PROCESS_QUEUE_LOCK:
        while True:
            if state.shutdown_flag.is_set():
                break

            # Use semaphore for limiting
            if not _SUBMISSION_THROTTLE.acquire(blocking=False):
                break

            # Claim item
            item = state.queue_manager.claim_next_downloadable()
            if not item:
                _SUBMISSION_THROTTLE.release()
                break

            # pylint: disable=consider-using-with
            with _ACTIVE_COUNT_LOCK:
                _ACTIVE_COUNT += 1

            # Submit to executor
            try:
                # We submit a wrapper that releases semaphore when done
                EXECUTOR.submit(_wrapped_download_task, item)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Failed to submit task: %s", e)
                with _ACTIVE_COUNT_LOCK:
                    _ACTIVE_COUNT -= 1
                _SUBMISSION_THROTTLE.release()

                state.queue_manager.update_item_status(
                    item.get("id"), "Error", {"error": "Failed to start"}
                )


def _wrapped_download_task(item):
    """Wrapper to ensure semaphore release."""
    # pylint: disable=global-statement
    global _ACTIVE_COUNT
    try:
        if not state.shutdown_flag.is_set():
            download_task(item)
        else:
            # Ensure item state is terminal when skipped due to shutdown
            try:
                item["status"] = "Cancelled"
                state.queue_manager.update_item_status(item.get("id"), "Cancelled")
                if HistoryManager:
                    HistoryManager.add_entry(
                        item.get("url"),
                        item.get("title"),
                        item.get("output_path", "."),
                        item.get("video_format", "best"),
                        "Cancelled",
                        "N/A",
                        "N/A",
                    )
            except Exception:  # pylint: disable=broad-exception-caught
                # best-effort; don't block cleanup
                logger.exception("Failed to mark item as cancelled on shutdown.")
    finally:
        _SUBMISSION_THROTTLE.release()
        with _ACTIVE_COUNT_LOCK:
            _ACTIVE_COUNT -= 1

        # Notify
        try:
            # Accessing protected member _has_work as designed for internal signaling
            # pylint: disable=protected-access
            with state.queue_manager._has_work:
                state.queue_manager._has_work.notify_all()
        except Exception:  # pylint: disable=broad-exception-caught
            pass


def _update_progress_ui(item: Dict[str, Any]):
    """Helper to update UI control if present."""
    if "control" in item:
        try:
            item["control"].update_progress()
        except Exception:  # pylint: disable=broad-exception-caught
            pass


def _progress_hook_factory(item: Dict[str, Any], cancel_token: CancelToken):
    """Creates a closure for the progress hook."""

    def progress_hook(d):
        try:
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
        except InterruptedError:
            # Re-raise cancellation to stop download promptly
            raise
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Progress hook error ignored: %s", e)

    return progress_hook


def _log_to_history(item: Dict[str, Any], filepath: Optional[str] = None):
    """Log completed download to history safely."""
    if not HistoryManager:
        logger.warning("HistoryManager not available for logging.")
        return

    try:
        HistoryManager.add_entry(
            item["url"],
            str(item.get("title", item["url"])),
            str(item.get("output_path", ".")),
            str(item.get("video_format", "best")),
            "Completed",
            str(item.get("size", "Unknown")),
            filepath or "N/A",
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
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
            download_item=item,  # Pass item for advanced callbacks/debugging
        )

        info = download_video(options)

        # Success
        state.queue_manager.update_item_status(
            item_id,
            "Completed",
            {"filename": info.get("filename", "Unknown"), "progress": 1.0},
        )
        # Update the item dict in place because download_task caller might hold reference
        # But queue manager update_item_status does it for the queue.
        item["status"] = (
            "Completed"  # Update local ref for test assertion if test uses this ref
        )

        _log_to_history(item, info.get("filepath"))
        _update_progress_ui(item)

    except Exception as e:  # pylint: disable=broad-exception-caught
        # Check for cancellation
        msg = str(e)
        is_cancelled = (
            "Cancelled" in msg
            or item.get("status") == "Cancelled"
            or (
                cancel_token is not None
                and hasattr(cancel_token, "cancelled")
                and cancel_token.cancelled
            )
        )
        if is_cancelled:
            logger.info("Download cancelled: %s", url)

            # Ensure status is definitely cancelled and reset progress
            state.queue_manager.update_item_status(
                item_id,
                "Cancelled",
                {"progress": 0, "speed": "", "eta": "", "size": ""},
            )
            item["status"] = "Cancelled"  # Update local ref
        else:
            logger.error("Download failed: %s", e, exc_info=True)
            state.queue_manager.update_item_status(item_id, "Error", {"error": str(e)})
            item["status"] = "Error"  # Update local ref

        _update_progress_ui(item)

    finally:
        # Cleanup
        if item_id:
            state.queue_manager.unregister_cancel_token(item_id)
