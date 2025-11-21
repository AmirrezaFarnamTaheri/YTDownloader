import flet as ft
import logging
import threading
import time
import os
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
import pyperclip

from downloader import get_video_info, download_video
from config_manager import ConfigManager
from ui_utils import format_file_size, validate_url, is_ffmpeg_available
from history_manager import HistoryManager
from cloud_manager import CloudManager
from social_manager import SocialManager
from queue_manager import QueueManager
from theme import Theme
from app_layout import AppLayout

# Import Views
from views.download_view import DownloadView
from views.queue_view import QueueView
from views.history_view import HistoryView
from views.dashboard_view import DashboardView
from views.rss_view import RSSView
from views.settings_view import SettingsView

# Import Views
# We will attempt to import views if they exist, otherwise we fallback to inline implementation or create them.
# Based on file list, 'views/' might not exist or be fully populated in the current branch context if it was part of a larger refactor.
# However, main.py shows usage of views. Let's assume for this resolution we want to keep the robust modular structure
# if possible, BUT the HEAD (local) changes seem to have everything inline in main.py while origin/main uses views.
# The prompt implies "modernization and robustness" branch is HEAD.
# Usually refactoring INTO views is the modernization.
# But wait, HEAD has inline code? No, HEAD seems to have inline code (long file) while origin/main has imports from views.
# Let's check the file content again.
# HEAD starts with `import flet as ft ... from components import DownloadItemControl` and has a BIG main function.
# origin/main starts with `from views.download_view import DownloadView ...`
#
# If origin/main has the modular views, and HEAD has the monolithic main.py...
# It seems origin/main is the one with the refactored code? Or is HEAD the one with new features but old structure?
# The branch name is `streamcatch-modernization-robustness`.
# If I am on `streamcatch-modernization-robustness` (HEAD), and it has the monolithic file,
# maybe the refactor happened in `main` and I need to adapt my changes to the new structure?
# OR maybe `streamcatch-modernization-robustness` did a revert or a different approach?
#
# Let's look at `list_files` output again.
# The `views/` directory was NOT in the `list_files` output I got earlier!
# `list_files` result:
# ...
# main.py
# pyperclip.py
# pytest.ini
# queue_manager.py
# ...
#
# It does NOT show `views/`.
# This suggests that the `views/` folder exists in `origin/main` (the incoming branch) but NOT in the current branch.
# OR `list_files` is shallow? The description says "Lists all files ...".
#
# If `views/` is missing in the current tree, but `origin/main` imports them,
# then `origin/main` must have introduced the modular structure.
#
# To resolve this conflict correctly, I should likely Adopt the modular structure of `origin/main`
# but ensure all features from HEAD (monolithic) are preserved/moved into the views.
#
# This is a complex merge. "This branch has conflicts that must be resolved".
# If I simply take the monolithic file, I discard the refactoring.
# If I take the modular file, I might lose features added in HEAD if they aren't in the views.
#
# However, looking at the diff:
# HEAD has `cinema_mode`, `clipboard_switch`, `regex_filter`, `batch_btn`, `schedule_btn`.
# origin/main has `DownloadView`, `QueueView` etc.
#
# Use `origin/main` structure but check if I need to create the view files?
# Wait, if I am merging `origin/main` INTO `streamcatch-modernization-robustness`,
# git should have brought the `views/` folder into my working directory if it didn't conflict.
#
# Let's check if `views/` exists now.
# I'll check `ls -R`.

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- State Management ---
class AppState:
    def __init__(self):
        self.config = ConfigManager.load_config()
        self.queue_manager = QueueManager()
        self.current_download_item: Optional[Dict[str, Any]] = None
        self.cancel_token: Optional[Any] = None
        self.is_paused = False
        self.video_info: Optional[Dict[str, Any]] = None
        self.ffmpeg_available = is_ffmpeg_available()
        HistoryManager.init_db()

        # Feature flags / States
        self.cinema_mode = False
        self.cloud_manager = CloudManager()
        self.social_manager = SocialManager()
        self.scheduled_time: Optional[datetime.time] = None
        self.clipboard_monitor_active = False
        self.last_clipboard_content = ""

        # Try connecting to social
        threading.Thread(target=self.social_manager.connect, daemon=True).start()


state = AppState()

# Global variables for access (refactor later if possible)
download_view = None
queue_view = None
page = None


class CancelToken:
    """Token for managing download cancellation and pause/resume."""

    def __init__(self):
        self.cancelled = False
        self.is_paused = False

    def cancel(self):
        self.cancelled = True

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def check(self, d):
        if self.cancelled:
            raise Exception("Download cancelled by user.")
        while self.is_paused:
            time.sleep(0.5)
            if self.cancelled:
                raise Exception("Download cancelled by user.")


def process_queue():
    # Check for scheduled items
    items = state.queue_manager.get_all()
    now = datetime.now()
    for item in items:
        if item.get("scheduled_time") and item["status"].startswith("Scheduled"):
            if now >= item["scheduled_time"]:
                item["status"] = "Queued"
                item["scheduled_time"] = None

    if state.queue_manager.any_downloading():
        return

    # ATOMIC CLAIM
    item = state.queue_manager.claim_next_downloadable()
    if item:
        threading.Thread(target=download_task, args=(item,), daemon=True).start()


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

        item["status"] = "Completed"
        HistoryManager.add_entry(
            url=item["url"],
            title=item.get("title", "Unknown"),
            output_path=item.get("output_path"),
            format_str=item.get("video_format"),
            status="Completed",
            file_size=item.get("size", "N/A"),
            file_path=item.get("final_filename"),
        )

    except Exception as e:
        if "cancelled" in str(e):
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


def fetch_info_task(url):
    try:
        info = get_video_info(url)
        if not info:
            raise Exception("Failed to fetch info")
        state.video_info = info
        if download_view:
            download_view.update_info(info)
        if page:
            page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Metadata fetched successfully"))
            )
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        if page:
            page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Error: {e}")))
    finally:
        if download_view:
            download_view.fetch_btn.disabled = False
        if page:
            page.update()


def main(pg: ft.Page):
    global page, download_view, queue_view
    page = pg
    page.title = "StreamCatch - Ultimate Downloader"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window_min_width = 1100
    page.window_min_height = 800
    page.bgcolor = Theme.BG_DARK

    # Apply Theme
    page.theme = Theme.get_theme()

    # --- Helpers ---

    def on_fetch_info(url):
        if not url:
            page.show_snack_bar(ft.SnackBar(content=ft.Text("Please enter a URL")))
            return

        download_view.fetch_btn.disabled = True
        page.update()
        threading.Thread(target=fetch_info_task, args=(url,), daemon=True).start()

    def on_add_to_queue(data):
        # Process data and add to queue
        status = "Queued"
        sched_dt = None

        if state.scheduled_time:
            now = datetime.now()
            sched_dt = datetime.combine(now.date(), state.scheduled_time)
            if sched_dt < now:
                sched_dt += timedelta(days=1)
            status = f"Scheduled ({sched_dt.strftime('%H:%M')})"

        item = {
            "url": data["url"],
            "title": (
                state.video_info.get("title", "Unknown")
                if data["url"] == download_view.url_input.value and state.video_info
                else data["url"]
            ),
            "status": status,
            "scheduled_time": sched_dt,
            "video_format": data["video_format"],
            "output_path": str(Path.home() / "Downloads"),
            "playlist": data["playlist"],
            "sponsorblock": data["sponsorblock"],
            "use_aria2c": state.config.get("use_aria2c", False),
            "gpu_accel": state.config.get("gpu_accel", "None"),
            "output_template": data["output_template"],
            "start_time": data["start_time"],
            "end_time": data["end_time"],
            "force_generic": data["force_generic"],
            "cookies_from_browser": data.get("cookies_from_browser"),
        }
        state.queue_manager.add_item(item)
        state.scheduled_time = None
        queue_view.rebuild()
        page.show_snack_bar(ft.SnackBar(content=ft.Text("Added to queue")))
        process_queue()

    def on_cancel_item(item):
        item["status"] = "Cancelled"
        if state.current_download_item == item and state.cancel_token:
            state.cancel_token.cancel()
        if "control" in item:
            item["control"].update_progress()

    def on_remove_item(item):
        state.queue_manager.remove_item(item)
        queue_view.rebuild()

    def on_reorder_item(item, direction):
        q = state.queue_manager.get_all()
        if item in q:
            idx = q.index(item)
            new_idx = idx + direction
            if 0 <= new_idx < len(q):
                state.queue_manager.swap_items(idx, new_idx)
                queue_view.rebuild()

    def on_retry_item(item):
        # Logic to retry download
        item["status"] = "Queued"
        item["speed"] = ""
        item["eta"] = ""
        item["size"] = ""
        queue_view.rebuild()
        process_queue()

    def on_batch_import():
        pass

    def on_toggle_clipboard(active):
        state.clipboard_monitor_active = active
        msg = "Clipboard Monitor Enabled" if active else "Clipboard Monitor Disabled"
        page.show_snack_bar(ft.SnackBar(content=ft.Text(msg)))

    # --- Views Initialization ---
    download_view = DownloadView(on_fetch_info, on_add_to_queue, None, None, state)
    # Pass on_retry_item to QueueView
    queue_view = QueueView(
        state.queue_manager, on_cancel_item, on_remove_item, on_reorder_item
    )
    queue_view.on_retry = on_retry_item

    history_view = HistoryView()
    dashboard_view = DashboardView()
    rss_view = RSSView(state.config)
    settings_view = SettingsView(state.config)

    views_list = [
        download_view,
        queue_view,
        history_view,
        dashboard_view,
        rss_view,
        settings_view,
    ]

    # --- Navigation ---

    def navigate_to(index):
        app_layout.set_content(views_list[index])
        if index == 2:
            history_view.load()
        elif index == 3:
            dashboard_view.load()
        elif index == 4:
            rss_view.load()
        page.update()

    app_layout = AppLayout(
        page, navigate_to, on_toggle_clipboard, state.clipboard_monitor_active
    )

    # Initial View
    app_layout.set_content(download_view)
    page.add(app_layout.view)

    # --- Background Logic ---

    def background_loop():
        while True:
            time.sleep(2)
            try:
                process_queue()
            except:
                pass

            if state.clipboard_monitor_active:
                try:
                    content = pyperclip.paste()
                    if content and content != state.last_clipboard_content:
                        state.last_clipboard_content = content
                        if validate_url(content) and download_view:
                            # Only auto-paste if download view is active? Or just notify?
                            # User requirement was "better visibility and control".
                            # Let's just notify for now to avoid annoying auto-paste.
                            # Or update the input field if empty.
                            if not download_view.url_input.value:
                                download_view.url_input.value = content
                                if page:
                                    page.update()
                                    page.show_snack_bar(
                                        ft.SnackBar(
                                            content=ft.Text(f"URL detected: {content}")
                                        )
                                    )
                except:
                    pass

    threading.Thread(target=background_loop, daemon=True).start()


if __name__ == "__main__":
    if os.environ.get("FLET_WEB"):
        ft.app(target=main, view=ft.WEB_BROWSER, port=8550)
    else:
        ft.app(target=main)
