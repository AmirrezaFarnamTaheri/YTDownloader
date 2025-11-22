import flet as ft
import logging
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
import os

from downloader import get_video_info
from theme import Theme
from app_layout import AppLayout

# Import Views
from views.download_view import DownloadView
from views.queue_view import QueueView
from views.history_view import HistoryView
from views.dashboard_view import DashboardView
from views.rss_view import RSSView
from views.settings_view import SettingsView

# Refactored modules
from app_state import state
from tasks import process_queue
from clipboard_monitor import start_clipboard_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variables for access
download_view = None
queue_view = None
page = None


def fetch_info_task(url):
    """Fetch video info in background with cookie support."""
    try:
        # Get selected browser cookies if available
        cookies_from_browser = None
        if download_view and hasattr(download_view, 'cookies_dd'):
            cookies_value = download_view.cookies_dd.value

            if cookies_value and cookies_value != "None":
                cookies_from_browser = cookies_value

        info = get_video_info(url, cookies_from_browser=cookies_from_browser)
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
            page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Please enter a URL"))
            )
            return

        download_view.fetch_btn.disabled = True
        page.update()

        threading.Thread(
            target=fetch_info_task, args=(url,), daemon=True
        ).start()

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

                if data["url"] == download_view.url_input.value
                and state.video_info
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
        # Placeholder for batch import logic
        pass

    def on_schedule(e):
        pass

    def on_toggle_clipboard(active):
        state.clipboard_monitor_active = active
        msg = (
            "Clipboard Monitor Enabled"
            if active
            else "Clipboard Monitor Disabled"
        )
        page.show_snack_bar(ft.SnackBar(content=ft.Text(msg)))

    # --- Views Initialization ---
    download_view = DownloadView(
        on_fetch_info, on_add_to_queue, on_batch_import, on_schedule, state
    )
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

    # Shutdown flag for graceful termination
    shutdown_flag = threading.Event()

    def background_loop():
        """Background loop for queue processing."""
        while not shutdown_flag.is_set():
            time.sleep(2)
            try:
                process_queue()
            except Exception as e:
                logger.error(f"Error in process_queue: {e}", exc_info=True)

    # Start Clipboard Monitor (it runs its own loop)
    start_clipboard_monitor(page, download_view)

    # Store shutdown flag in page for cleanup
    page.on_disconnect = lambda _: shutdown_flag.set()

    threading.Thread(target=background_loop, daemon=True).start()


if __name__ == "__main__":
    if os.environ.get("FLET_WEB"):
        ft.app(target=main, view=ft.WEB_BROWSER, port=8550)
    else:
        ft.app(target=main)
