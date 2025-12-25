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
from ui_utils import get_default_download_path
from utils import CancelToken

logger = logging.getLogger(__name__)

# Default max workers - will be initialized lazily
DEFAULT_MAX_WORKERS = 3
_executor = None
_executor_lock = threading.Lock()


def _get_executor():
    """Lazily initialize executor to allow config changes before first use."""
    global _executor
    with _executor_lock:
        if _executor is None:
            max_workers = state.config.get(
                "max_concurrent_downloads", DEFAULT_MAX_WORKERS
            )
            _executor = ThreadPoolExecutor(
                max_workers=max_workers, thread_name_prefix="DLWorker"
            )
        return _executor


# For backwards compatibility - mimic EXECUTOR global via module getattr
# Python 3.7+ supports __getattr__ at module level
def __getattr__(name):
    if name == "EXECUTOR":
        return _get_executor()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Tracks the number of actively running downloads
_active_count = 0
_active_count_lock = threading.Lock()


def _get_max_workers():
    try:
        return int(state.config.get("max_concurrent_downloads", DEFAULT_MAX_WORKERS))
    except Exception:  # pylint: disable=broad-exception-caught
        return DEFAULT_MAX_WORKERS


# Throttle submission to executor to avoid flooding it with tasks.
# We limit the number of submitted-but-not-finished tasks to MAX_WORKERS.
# This prevents queuing up 100 tasks in the executor when only 3 can run at once,
# which allows for more responsive cancellation and priority handling.
_submission_throttle = threading.Semaphore(_get_max_workers())

# Lock for protecting the queue processing loop
_PROCESS_QUEUE_LOCK = threading.RLock()


def process_queue():
    """
    Process items in the queue.
    Submits new downloads to the executor if slots are available.
    """
    # pylint: disable=global-statement
    global _active_count

    if state.shutdown_flag.is_set():
        return

    with _PROCESS_QUEUE_LOCK:
        while True:
            if state.shutdown_flag.is_set():
                break

            # Try to acquire a slot without blocking
            # pylint: disable=consider-using-with
            if _submission_throttle.acquire(blocking=False):
                try:
                    # We acquired a slot, check if there is work
                    item = state.queue_manager.claim_next_downloadable()
                    if not item:
                        # No work, release slot immediately
                        _submission_throttle.release()
                        break
                    logger.debug(
                        "Claimed item for download: %s", item.get("id", "unknown")
                    )
                except Exception:
                    # Ensure release if claim fails
                    _submission_throttle.release()
                    raise
            else:
                # No slots available
                break

            # Increment active count for monitoring
            # pylint: disable=consider-using-with
            with _active_count_lock:
                _active_count += 1

            # Submit to executor
            try:
                # We submit a wrapper that releases semaphore when done
                _get_executor().submit(_wrapped_download_task, item)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Failed to submit task: %s", e)
                with _active_count_lock:
                    _active_count -= 1
                _submission_throttle.release()

                state.queue_manager.update_item_status(
                    item.get("id"), "Error", {"error": "Failed to start"}
                )


def _wrapped_download_task(item):
    """
    Wrapper to ensure semaphore release and accurate active count.
    Guarantees semaphore is released even if download_task fails or app shuts down.
    """
    # pylint: disable=global-statement
    global _active_count
    try:
        if not state.shutdown_flag.is_set():
            download_task(item)
        else:
            # Ensure item state is terminal when skipped due to shutdown
            try:
                item["status"] = "Cancelled"
                state.queue_manager.update_item_status(item.get("id"), "Cancelled")
                _log_to_history(item, None)
            except Exception:  # pylint: disable=broad-exception-caught
                # best-effort; don't block cleanup
                logger.exception("Failed to mark item as cancelled on shutdown.")
    finally:
        # ALWAYS release semaphore and decrement count
        _submission_throttle.release()
        with _active_count_lock:
            _active_count -= 1
            logger.debug("Active downloads decremented to %d", _active_count)

        # Notify queue manager that a slot opened up
        try:
            # Accessing protected member _has_work as designed for internal signaling
            # pylint: disable=protected-access
            with state.queue_manager._has_work:
                state.queue_manager._has_work.notify_all()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug(
                "Failed to notify queue manager for slot release: %s",
                exc,
                exc_info=True,
            )


def configure_concurrency(max_workers: Optional[int] = None) -> bool:
    """
    Update executor/semaphore concurrency. Returns True if applied.
    Will not modify when active downloads are running.
    """
    global _executor, _submission_throttle

    if max_workers is None:
        max_workers = _get_max_workers()

    try:
        max_workers = int(max_workers)
    except (ValueError, TypeError):
        logger.warning("Invalid max_workers value: %s", max_workers)
        return False

    if max_workers < 1:
        logger.warning("max_workers must be >= 1")
        return False

    with _active_count_lock:
        if _active_count > 0:
            logger.warning(
                "Skipping concurrency update while %d downloads are active",
                _active_count,
            )
            return False

    with _executor_lock:
        if _executor is not None:
            try:
                _executor.shutdown(wait=False)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.debug(
                    "Executor shutdown failed during reconfigure", exc_info=True
                )
            _executor = ThreadPoolExecutor(
                max_workers=max_workers, thread_name_prefix="DLWorker"
            )

    _submission_throttle = threading.Semaphore(max_workers)
    logger.info("Updated concurrency limit to %d", max_workers)
    return True


def _update_progress_ui(item: Dict[str, Any]):
    """Helper to update UI control if present."""
    if "control" in item:
        try:
            item["control"].update_progress()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("Failed to update progress UI: %s", exc, exc_info=True)


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

        except InterruptedError:
            # Re-raise cancellation to stop download promptly
            raise
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Progress hook error ignored: %s", e)

    return progress_hook


def _log_to_history(item: Dict[str, Any], filepath: Optional[str] = None):
    """Log completed download to history safely."""
    # Import locally to avoid circular import issues at top-level
    # pylint: disable=import-outside-toplevel
    try:
        from history_manager import HistoryManager

        status = item.get("status", "Unknown")
        HistoryManager.add_entry(
            item["url"],
            str(item.get("title", item["url"])),
            str(item.get("output_path", ".")),
            str(item.get("video_format", "best")),
            status,
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

    if item_id:
        current = state.queue_manager.get_item_by_id(item_id)
        if not current:
            logger.info("Skipping removed item before download start: %s", item_id)
            return
        if str(current.get("status")) == "Cancelled":
            logger.info("Skipping cancelled item before download start: %s", item_id)
            state.queue_manager.update_item_status(item_id, "Cancelled")
            return

    if str(item.get("status")) == "Cancelled":
        logger.info("Skipping cancelled item before download start: %s", item_id)
        return

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

        preferred_path = None
        if hasattr(state, "config") and hasattr(state.config, "get"):
            preferred_path = state.config.get("download_path")
        output_path = item.get("output_path") or get_default_download_path(
            preferred_path
        )
        if not item.get("output_path"):
            item["output_path"] = output_path
        logger.debug("Resolved output path for %s: %s", url, output_path)

        proxy = item.get("proxy")
        if not proxy and hasattr(state, "config") and hasattr(state.config, "get"):
            cfg_proxy = state.config.get("proxy")
            proxy = cfg_proxy if isinstance(cfg_proxy, str) and cfg_proxy else None
        if proxy:
            logger.debug("Proxy enabled for %s", url)

        rate_limit = item.get("rate_limit")
        if not rate_limit and hasattr(state, "config") and hasattr(state.config, "get"):
            cfg_rate = state.config.get("rate_limit")
            rate_limit = cfg_rate if isinstance(cfg_rate, str) and cfg_rate else None
        if rate_limit:
            logger.debug("Rate limit set for %s: %s", url, rate_limit)

        # Map dict item to DownloadOptions
        output_template = item.get("output_template") or "%(title)s.%(ext)s"
        if not isinstance(output_template, str):
            output_template = "%(title)s.%(ext)s"

        options = DownloadOptions(
            url=url,
            output_path=output_path,
            video_format=item.get("video_format", "best"),
            progress_hook=phook,
            cancel_token=cancel_token,
            playlist=item.get("playlist", False),
            sponsorblock=item.get("sponsorblock", False),
            use_aria2c=item.get("use_aria2c", False),
            gpu_accel=item.get("gpu_accel"),
            output_template=output_template,
            start_time=item.get("start_time"),
            end_time=item.get("end_time"),
            force_generic=item.get("force_generic", False),
            cookies_from_browser=item.get("cookies_from_browser"),
            subtitle_lang=item.get("subtitle_lang"),
            subtitle_format=item.get("subtitle_format"),
            split_chapters=item.get("chapters", False),
            proxy=proxy,
            rate_limit=rate_limit,
            download_item=item,  # Pass item for advanced callbacks/debugging
        )

        info = download_video(options)

        # Success
        state.queue_manager.update_item_status(
            item_id,
            "Completed",
            {
                "filename": info.get("filename", "Unknown"),
                "filepath": info.get("filepath", "Unknown"),
                "progress": 1.0,
            },
        )
        logger.info("Download completed: %s", url)
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
