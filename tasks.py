import threading
import logging
from datetime import datetime

from downloader import download_video
from ui_utils import format_file_size
from history_manager import HistoryManager
from app_state import state
from utils import CancelToken

logger = logging.getLogger(__name__)

# Lock to prevent concurrent process_queue calls
_process_queue_lock = threading.Lock()


def process_queue():
    """
    Process the queue to start the next download.
    Uses a lock to prevent race conditions from concurrent calls.
    """
    # Acquire lock to prevent concurrent processing
    if not _process_queue_lock.acquire(blocking=False):
        # Another thread is already processing, skip
        return

    try:
        # Check for scheduled items and update them atomically
        now = datetime.now()
        with state.queue_manager._lock:
            for item in state.queue_manager._queue:
                if item.get("scheduled_time") and str(item["status"]).startswith(
                    "Scheduled"
                ):
                    if now >= item["scheduled_time"]:
                        item["status"] = "Queued"
                        item["scheduled_time"] = None

        if state.queue_manager.any_downloading():
            return

        # ATOMIC CLAIM
        item = state.queue_manager.claim_next_downloadable()
        if item:
            threading.Thread(target=download_task, args=(item,), daemon=True).start()
    finally:
        _process_queue_lock.release()


def download_task(item):
    item["status"] = "Downloading"
    state.current_download_item = item
    state.cancel_token = CancelToken()

    if "control" in item:
        item["control"].update_progress()

    try:

        def progress_hook(d, _):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = downloaded / total
                    if "control" in item:
                        item["control"].progress_bar.value = pct

                item["speed"] = format_file_size(d.get("speed", 0)) + "/s"
                item["size"] = format_file_size(total)
                item["eta"] = f"{d.get('eta', 0)}s"

                if "control" in item:
                    item["control"].update_progress()

            elif d["status"] == "finished":
                item["status"] = "Processing"
                if "control" in item:
                    item["control"].progress_bar.value = 1.0
                    item["control"].update_progress()
                item["final_filename"] = d.get("filename")

        # Extract cookies if passed
        cookies = item.get("cookies_from_browser")

        download_video(
            item["url"],
            progress_hook,
            item,
            video_format=item.get("video_format", "best"),
            output_path=item.get("output_path"),
            cancel_token=state.cancel_token,
            sponsorblock_remove=item.get("sponsorblock", False),
            playlist=item.get("playlist", False),
            use_aria2c=item.get("use_aria2c", False),
            gpu_accel=item.get("gpu_accel"),
            output_template=item.get("output_template"),
            start_time=item.get("start_time"),
            end_time=item.get("end_time"),
            force_generic=item.get("force_generic", False),
            cookies_from_browser=cookies,
        )

        # Add to history first, then mark as completed
        try:
            HistoryManager.add_entry(
                url=item["url"],
                title=item.get("title", "Unknown"),
                output_path=item.get("output_path"),
                format_str=item.get("video_format"),
                status="Completed",
                file_size=item.get("size", "N/A"),
                file_path=item.get("final_filename"),
            )
        except Exception as history_error:
            logger.error(f"Failed to add entry to history: {history_error}")
            # Continue anyway - download succeeded even if history failed

        item["status"] = "Completed"

    except Exception as e:
        if "cancelled" in str(e).lower():
            item["status"] = "Cancelled"
        else:
            item["status"] = "Error"
            logger.error(f"Download failed: {e}")
    finally:
        if "control" in item:
            item["control"].update_progress()
        state.current_download_item = None
        state.cancel_token = None
        process_queue()
