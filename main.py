import flet as ft
import logging
import threading
import time
import os
from typing import Dict, Any, Optional, List
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
from components import DownloadItemControl

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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

        # UX States
        self.selected_queue_index = -1
        self.high_contrast = False
        self.selected_nav_index = 0
        self.last_clipboard_content = ""

        # Try connecting to social
        threading.Thread(target=self.social_manager.connect, daemon=True).start()

state = AppState()

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

# Global variables for UI access
page = None
download_view = None
queue_view = None

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
            match_filter=item.get("match_filter"),
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


def main(pg: ft.Page):
    global page, download_view, queue_view
    page = pg
    page.title = "StreamCatch - Ultimate Downloader"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window_min_width = 1100
    page.window_min_height = 800
    page.bgcolor = ft.Colors.BLACK

    # Apply a custom modern theme
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.INDIGO,
        font_family="Roboto",
        use_material3=True
    )

    # Since we have a conflict between monolithic structure and modular structure,
    # and the views/ directory might not be fully populated in this environment yet
    # (as hinted by list_files), we will stick to the monolithic structure from HEAD
    # but incorporate improvements from origin/main where possible (like helper functions).

    # --- UI Components ---

    # 1. Navigation Rail (Left Sidebar)
    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        group_alignment=-0.9,
        bgcolor=ft.Colors.GREY_900,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.DOWNLOAD_ROUNDED, selected_icon=ft.Icons.DOWNLOAD_DONE_ROUNDED, label="Download"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.QUEUE_MUSIC_ROUNDED, selected_icon=ft.Icons.QUEUE_MUSIC, label="Queue"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.HISTORY_TOGGLE_OFF_ROUNDED, selected_icon=ft.Icons.HISTORY, label="History"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD_CUSTOMIZE_ROUNDED, selected_icon=ft.Icons.DASHBOARD, label="Dashboard"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.RSS_FEED_ROUNDED, label="RSS"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_ROUNDED, label="Settings"
            ),
        ],
        on_change=lambda e: navigate_to(e.control.selected_index),
    )

    # --- Download Tab Content ---

    platform_icons = ft.Row([
        ft.Icon(ft.Icons.SMART_DISPLAY, color=ft.Colors.RED_400, tooltip="YouTube"),
        ft.Icon(ft.Icons.TELEGRAM, color=ft.Colors.BLUE_400, tooltip="Telegram"),
        ft.Icon(ft.Icons.ALTERNATE_EMAIL, color=ft.Colors.LIGHT_BLUE_400, tooltip="Twitter/X"),
        ft.Icon(ft.Icons.CAMERA_ALT, color=ft.Colors.PINK_400, tooltip="Instagram"),
        ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color=ft.Colors.GREY_400, tooltip="Generic Files"),
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=30)

    url_input = ft.TextField(
        label="Paste Link",
        hint_text="YouTube, Telegram, Twitter, Instagram, or direct links...",
        expand=True,
        border_color=ft.Colors.BLUE_400,
        prefix_icon=ft.Icons.LINK,
        text_size=16,
        bgcolor=ft.Colors.GREY_900,
        border_radius=12
    )

    clipboard_switch = ft.Switch(
        label="Clipboard Monitor",
        value=False,
        on_change=lambda e: toggle_clipboard_monitor(e.control.value),
        active_color=ft.Colors.BLUE_400
    )

    thumbnail_img = ft.Image(src="", width=400, height=225, fit=ft.ImageFit.COVER, border_radius=12, visible=False)
    title_text = ft.Text("", size=22, weight=ft.FontWeight.BOLD, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
    duration_text = ft.Text("", color=ft.Colors.GREY_400, size=14)

    video_format_dd = ft.Dropdown(label="Video Quality", options=[], expand=True, border_color=ft.Colors.GREY_700, border_radius=12, text_size=14)
    audio_format_dd = ft.Dropdown(label="Audio Format", options=[], expand=True, border_color=ft.Colors.GREY_700, border_radius=12, text_size=14)

    playlist_cb = ft.Checkbox(label="Playlist", fill_color=ft.Colors.BLUE_400)
    sponsorblock_cb = ft.Checkbox(label="SponsorBlock", fill_color=ft.Colors.BLUE_400)
    force_generic_cb = ft.Checkbox(label="Force Generic", fill_color=ft.Colors.ORANGE_400, tooltip="Bypass extraction")

    subtitle_dd = ft.Dropdown(label="Subtitles", options=[ft.dropdown.Option("None"), ft.dropdown.Option("en"), ft.dropdown.Option("es")], value="None", width=160, border_color=ft.Colors.GREY_700, border_radius=12)

    time_start = ft.TextField(label="Start (HH:MM:SS)", width=160, border_color=ft.Colors.GREY_700, border_radius=12, text_size=14)
    time_end = ft.TextField(label="End (HH:MM:SS)", width=160, border_color=ft.Colors.GREY_700, border_radius=12, text_size=14)
    regex_filter = ft.TextField(label="Playlist Regex Filter", expand=True, border_color=ft.Colors.GREY_700, border_radius=12, text_size=14)

    def on_file_picker_result(e: ft.FilePickerResultEvent):
        if e.files:
            file_path = e.files[0].path
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

                valid_urls = [u for u in urls if validate_url(u)]
                if not valid_urls:
                    page.show_snack_bar(ft.SnackBar(content=ft.Text("No valid URLs found")))
                    return

                count = 0
                for url in valid_urls:
                    _add_url_to_queue(url, custom_title=url)
                    count += 1
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Imported {count} URLs")))
                rebuild_queue_ui()
            except Exception as ex:
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Import Error: {ex}")))

    file_picker = ft.FilePicker(on_result=on_file_picker_result)
    page.overlay.append(file_picker)

    batch_btn = ft.TextButton("Batch Import", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: file_picker.pick_files(allow_multiple=False, allowed_extensions=['txt']))

    schedule_time_picker = ft.TimePicker(confirm_text="Schedule", error_invalid_text="Time out of range")
    def on_time_picked(e):
        state.scheduled_time = schedule_time_picker.value
        page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Scheduled download for {state.scheduled_time.strftime('%H:%M')}")))
    schedule_time_picker.on_change = on_time_picked
    page.overlay.append(schedule_time_picker)

    schedule_btn = ft.TextButton("Schedule", icon=ft.Icons.SCHEDULE, on_click=lambda _: schedule_time_picker.pick_time())

    download_btn = ft.ElevatedButton(
        "Add to Queue",
        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
        bgcolor=ft.Colors.BLUE_600,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=16),
            padding=24,
            elevation=4,
        ),
        on_click=lambda e: add_to_queue(e)
    )

    fetch_btn = ft.IconButton(
        ft.Icons.SEARCH_ROUNDED,
        on_click=lambda e: fetch_info_click(e),
        tooltip="Fetch Info",
        icon_color=ft.Colors.BLUE_400,
        icon_size=32,
        style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_900, shape=ft.RoundedRectangleBorder(radius=12))
    )

    download_view = ft.Container(
        padding=40,
        content=ft.Column([
            ft.Row([
                ft.Text("StreamCatch", size=36, weight=ft.FontWeight.W_900, color=ft.Colors.WHITE, font_family="Roboto"),
                ft.Container(content=clipboard_switch, bgcolor=ft.Colors.GREY_900, padding=10, border_radius=12)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=20),
            platform_icons,
            ft.Container(height=20),
            ft.Row([url_input, ft.Container(width=10), fetch_btn], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(height=40, color=ft.Colors.GREY_800),
            ft.Row([
                ft.Column([
                    ft.Container(
                        content=ft.Stack([
                             ft.Container(bgcolor=ft.Colors.BLACK87, width=400, height=225, border_radius=12),
                             thumbnail_img
                        ]),
                        border_radius=12,
                        border=ft.border.all(1, ft.Colors.GREY_800),
                        shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.BLACK)
                    ),
                    title_text,
                    duration_text
                ], alignment=ft.MainAxisAlignment.START, width=420),
                ft.Container(width=40),
                ft.Column([
                    ft.Container(
                        padding=25,
                        bgcolor=ft.Colors.GREY_900,
                        border_radius=16,
                        border=ft.border.all(1, ft.Colors.GREY_800),
                        content=ft.Column([
                            ft.Text("Quality & Format", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                            ft.Row([video_format_dd, audio_format_dd]),
                            ft.Container(height=10),
                            ft.Text("Options", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                            ft.Row([playlist_cb, sponsorblock_cb, force_generic_cb]),
                            ft.Row([subtitle_dd, time_start, time_end]),
                            ft.Row([regex_filter]),
                            ft.Divider(color=ft.Colors.GREY_800),
                            ft.Row([batch_btn, schedule_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ])
                    ),
                    ft.Container(height=20),
                    ft.Row([download_btn], alignment=ft.MainAxisAlignment.END)
                ], expand=True)
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
        ], scroll=ft.ScrollMode.AUTO)
    )

    # --- Queue Tab Content ---
    queue_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def clear_queue(e):
        to_remove = [item for item in state.queue_manager.get_all() if item['status'] not in ('Downloading', 'Allocating', 'Processing')]
        for item in to_remove:
            state.queue_manager.remove_item(item)
        rebuild_queue_ui()

    queue_view = ft.Container(
        padding=40,
        content=ft.Column([
            ft.Row([
                ft.Text("Download Queue", size=28, weight=ft.FontWeight.BOLD),
                ft.OutlinedButton("Clear Queue", icon=ft.Icons.CLEAR_ALL, on_click=clear_queue)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color=ft.Colors.GREY_800),
            queue_list
        ], expand=True)
    )

    # --- History Tab Content ---
    history_list = ft.ListView(expand=True, spacing=10)
    def load_history():
        history_list.controls.clear()
        items = HistoryManager.get_history(limit=50)
        for item in items:
            history_list.controls.append(
                ft.Container(
                    padding=15,
                    bgcolor=ft.Colors.GREY_900,
                    border_radius=12,
                    border=ft.border.all(1, ft.Colors.GREY_800),
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=ft.Colors.GREEN_400),
                        ft.Column([
                            ft.Text(item.get('title', item['url']), weight=ft.FontWeight.BOLD, overflow=ft.TextOverflow.ELLIPSIS, width=450, size=16),
                            ft.Text(f"{item.get('timestamp')} • {item.get('file_size', 'N/A')}", size=12, color=ft.Colors.GREY_500)
                        ]),
                        ft.Container(expand=True),
                        ft.IconButton(ft.Icons.FOLDER_OPEN, tooltip="Open Folder", on_click=lambda e, p=item.get('output_path'): open_folder(p)),
                        ft.IconButton(ft.Icons.COPY, tooltip="Copy URL", on_click=lambda e, u=item['url']: page.set_clipboard(u))
                    ])
                )
            )
        page.update()

    def open_folder(path):
        import subprocess, platform
        if not path: return
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as ex:
            logger.error(f"Failed to open folder: {ex}")
            page.show_snack_bar(ft.SnackBar(content=ft.Text("Could not open folder")))

    def clear_history_action():
        HistoryManager.clear_history()
        load_history()
        page.show_snack_bar(ft.SnackBar(content=ft.Text("History cleared")))

    history_view = ft.Container(
        padding=40,
        content=ft.Column([
            ft.Row([
                ft.Text("History", size=28, weight=ft.FontWeight.BOLD),
                ft.OutlinedButton("Clear History", icon=ft.Icons.DELETE_SWEEP, on_click=lambda e: clear_history_action())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color=ft.Colors.GREY_800),
            history_list
        ], expand=True)
    )

    # --- Dashboard Content ---
    dashboard_stats_row = ft.Row(wrap=True, spacing=20)
    def load_dashboard():
        dashboard_stats_row.controls.clear()
        history = HistoryManager.get_history(limit=1000)
        total_downloads = len(history)
        total_size_mb = 0
        for h in history:
            size_str = h.get('file_size', '0')
            if 'MB' in size_str:
                try: total_size_mb += float(size_str.split()[0])
                except: pass
            elif 'GB' in size_str:
                try: total_size_mb += float(size_str.split()[0]) * 1024
                except: pass

        card_total = ft.Container(
            padding=25, bgcolor=ft.Colors.BLUE_900, border_radius=20, width=260, height=160,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.BLACK45),
            content=ft.Column([
                ft.Icon(ft.Icons.DOWNLOAD_DONE_ROUNDED, size=48, color=ft.Colors.WHITE),
                ft.Text(str(total_downloads), size=42, weight=ft.FontWeight.BOLD),
                ft.Text("Total Downloads", color=ft.Colors.BLUE_100, size=14)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
        )
        card_size = ft.Container(
            padding=25, bgcolor=ft.Colors.INDIGO_900, border_radius=20, width=260, height=160,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.BLACK45),
            content=ft.Column([
                ft.Icon(ft.Icons.SD_STORAGE_ROUNDED, size=48, color=ft.Colors.WHITE),
                ft.Text(f"{int(total_size_mb/1024)} GB", size=42, weight=ft.FontWeight.BOLD),
                ft.Text("Total Size", color=ft.Colors.INDIGO_100, size=14)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
        )
        dashboard_stats_row.controls.extend([card_total, card_size])
        page.update()

    dashboard_view = ft.Container(
        padding=40,
        content=ft.Column([
            ft.Text("Dashboard", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(color=ft.Colors.GREY_800),
            dashboard_stats_row,
            ft.Divider(color=ft.Colors.TRANSPARENT, height=30),
            ft.Text("Recent Activity", size=20, weight=ft.FontWeight.BOLD),
        ])
    )

    # --- RSS Content ---
    rss_input = ft.TextField(label="Feed URL", expand=True, border_color=ft.Colors.GREY_700, border_radius=12)
    rss_list_view = ft.ListView(expand=True)

    def load_rss_feeds():
        rss_list_view.controls.clear()
        for feed in state.config.get('rss_feeds', []):
            rss_list_view.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.RSS_FEED, color=ft.Colors.ORANGE_400),
                    title=ft.Text(feed, weight=ft.FontWeight.W_500),
                    trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, on_click=lambda e, f=feed: remove_rss(f))
                )
            )
        page.update()

    def add_rss(e):
        if not rss_input.value: return
        feeds = state.config.get('rss_feeds', [])
        if rss_input.value not in feeds:
            feeds.append(rss_input.value)
            state.config['rss_feeds'] = feeds
            ConfigManager.save_config(state.config)
            load_rss_feeds()
            rss_input.value = ""
            page.update()

    def remove_rss(feed):
        feeds = state.config.get('rss_feeds', [])
        if feed in feeds:
            feeds.remove(feed)
            state.config['rss_feeds'] = feeds
            ConfigManager.save_config(state.config)
            load_rss_feeds()

    rss_view = ft.Container(
        padding=40,
        content=ft.Column([
            ft.Text("RSS Manager", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(color=ft.Colors.GREY_800),
            ft.Row([rss_input, ft.IconButton(ft.Icons.ADD_CIRCLE, on_click=add_rss, icon_size=48, icon_color=ft.Colors.BLUE_400)]),
            rss_list_view
        ], expand=True)
    )

    # --- Settings Content ---
    proxy_input = ft.TextField(label="Proxy URL", value=state.config.get('proxy', ''), border_color=ft.Colors.GREY_700, border_radius=12)
    rate_limit_input = ft.TextField(label="Rate Limit (e.g. 5M)", value=state.config.get('rate_limit', ''), border_color=ft.Colors.GREY_700, border_radius=12)
    output_template_input = ft.TextField(label="Output Filename Template", value=state.config.get('output_template', '%(title)s.%(ext)s'), border_color=ft.Colors.GREY_700, border_radius=12)
    use_aria2c_cb = ft.Checkbox(label="Enable Aria2c Accelerator", value=state.config.get('use_aria2c', False))
    gpu_accel_dd = ft.Dropdown(label="GPU Acceleration", options=[
        ft.dropdown.Option("None"), ft.dropdown.Option("auto"), ft.dropdown.Option("cuda"), ft.dropdown.Option("vulkan")
    ], value=state.config.get('gpu_accel', 'None'), border_color=ft.Colors.GREY_700, border_radius=12)

    def save_settings(e):
        state.config['proxy'] = proxy_input.value
        state.config['rate_limit'] = rate_limit_input.value
        state.config['output_template'] = output_template_input.value
        state.config['use_aria2c'] = use_aria2c_cb.value
        state.config['gpu_accel'] = gpu_accel_dd.value
        ConfigManager.save_config(state.config)
        page.show_snack_bar(ft.SnackBar(content=ft.Text("Settings saved successfully!")))

    settings_view = ft.Container(
        padding=40,
        content=ft.Column([
            ft.Text("Settings", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(color=ft.Colors.GREY_800),
            ft.Text("Network", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
            proxy_input,
            rate_limit_input,
            ft.Container(height=10),
            ft.Text("Filesystem", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
            output_template_input,
            ft.Container(height=10),
            ft.Text("Performance", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
            use_aria2c_cb,
            gpu_accel_dd,
            ft.Divider(height=30, color=ft.Colors.GREY_800),
            ft.ElevatedButton("Save Configuration", on_click=save_settings, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, style=ft.ButtonStyle(padding=20, shape=ft.RoundedRectangleBorder(radius=12)))
        ], scroll=ft.ScrollMode.AUTO)
    )

    content_area = ft.Container(expand=True, bgcolor=ft.Colors.BLACK)
    views = [download_view, queue_view, history_view, dashboard_view, rss_view, settings_view]

    def navigate_to(index):
        state.selected_nav_index = index
        content_area.content = views[index]
        if index == 2: load_history()
        elif index == 3: load_dashboard()
        elif index == 4: load_rss_feeds()
        page.update()

    content_area.content = views[0]

    layout = ft.Row([
        nav_rail,
        ft.VerticalDivider(width=1, color=ft.Colors.GREY_900),
        content_area
    ], expand=True, spacing=0)

    cinema_overlay = ft.Container(
        visible=False, expand=True, bgcolor=ft.Colors.BLACK, alignment=ft.alignment.center,
        content=ft.Column([
             ft.Icon(ft.Icons.MOVIE_FILTER_ROUNDED, size=64, color=ft.Colors.BLUE_400),
             ft.Text("Cinema Mode", size=32, weight=ft.FontWeight.BOLD),
             ft.Container(height=20),
             ft.ProgressBar(width=600, height=10, color=ft.Colors.BLUE_400, bgcolor=ft.Colors.GREY_800, border_radius=5),
             ft.Container(height=10),
             ft.Text("Downloading...", color=ft.Colors.GREY_400, size=16),
             ft.Container(height=40),
             ft.OutlinedButton("Exit Mode", on_click=lambda e: toggle_cinema_mode(False), style=ft.ButtonStyle(padding=20))
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    page.add(ft.Stack([layout, cinema_overlay], expand=True))

    def toggle_cinema_mode(enable):
        state.cinema_mode = enable
        cinema_overlay.visible = enable
        page.update()

    def toggle_clipboard_monitor(enable):
        state.clipboard_monitor_active = enable
        msg = "Clipboard Monitor Started" if enable else "Clipboard Monitor Stopped"
        page.show_snack_bar(ft.SnackBar(content=ft.Text(msg)))

    def fetch_info_click(e):
        url = url_input.value
        if not url:
             page.show_snack_bar(ft.SnackBar(content=ft.Text("Please enter a URL")))
             return
        fetch_btn.disabled = True
        page.update()
        threading.Thread(target=fetch_info_task, args=(url,), daemon=True).start()

    def fetch_info_task(url):
        try:
            info = get_video_info(url)
            if not info: raise Exception("Failed to fetch info")
            state.video_info = info
            thumbnail_img.src = info.get('thumbnail') or ""
            thumbnail_img.visible = True
            title_text.value = info.get('title', 'N/A')
            duration_text.value = info.get('duration', '')

            video_streams = info.get('video_streams', [])
            video_opts = []
            for s in video_streams:
                label = f"{s.get('resolution', 'N/A')} ({s.get('ext', '?')})"
                if s.get('filesize'):
                    label += f" - {format_file_size(s['filesize'])}"
                video_opts.append(ft.dropdown.Option(key=s['format_id'], text=label))
            video_format_dd.options = video_opts
            if video_opts:
                video_format_dd.value = video_opts[0].key
                video_format_dd.disabled = False
            else:
                video_format_dd.options = [ft.dropdown.Option(key="best", text="Best / Direct")]
                video_format_dd.value = "best"
                video_format_dd.disabled = True

            audio_opts = [ft.dropdown.Option(key=s['format_id'], text=f"{s.get('abr', 'N/A')}kbps ({s.get('ext', '?')})") for s in info.get('audio_streams', [])]
            audio_format_dd.options = audio_opts
            if audio_opts:
                audio_format_dd.value = audio_opts[0].key
                audio_format_dd.disabled = False
            else:
                audio_format_dd.options = []
                audio_format_dd.value = None
                audio_format_dd.disabled = True

            page.show_snack_bar(ft.SnackBar(content=ft.Text("Metadata fetched successfully")))
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Error: {e}")))
        finally:
            fetch_btn.disabled = False
            page.update()

    def _add_url_to_queue(url_val, custom_title=None):
        status = "Queued"
        sched_dt = None
        if state.scheduled_time:
             now = datetime.now()
             sched_dt = datetime.combine(now.date(), state.scheduled_time)
             if sched_dt < now:
                 sched_dt += timedelta(days=1)
             status = f"Scheduled ({sched_dt.strftime('%H:%M')})"

        item = {
            "url": url_val,
            "title": custom_title or (state.video_info.get('title', 'Unknown') if url_val == url_input.value and state.video_info else url_val),
            "status": status,
            "scheduled_time": sched_dt,
            "video_format": video_format_dd.value,
            "output_path": str(Path.home() / "Downloads"),
            "playlist": playlist_cb.value,
            "sponsorblock": sponsorblock_cb.value,
            "use_aria2c": use_aria2c_cb.value,
            "gpu_accel": gpu_accel_dd.value,
            "output_template": output_template_input.value,
            "start_time": time_start.value,
            "end_time": time_end.value,
            "match_filter": regex_filter.value,
            "force_generic": force_generic_cb.value
        }
        state.queue_manager.add_item(item)

    def add_to_queue(e):
        _add_url_to_queue(url_input.value)
        state.scheduled_time = None
        rebuild_queue_ui()
        page.show_snack_bar(ft.SnackBar(content=ft.Text("Added to queue")))
        process_queue()

    def on_cancel_item(item):
        item['status'] = 'Cancelled'
        if state.current_download_item == item and state.cancel_token:
            state.cancel_token.cancel()
        if 'control' in item:
            item['control'].update_progress()

    def on_remove_item(item):
        state.queue_manager.remove_item(item)
        rebuild_queue_ui()

    def on_reorder_item(item, direction):
        q = state.queue_manager.get_all()
        if item in q:
            idx = q.index(item)
            new_idx = idx + direction
            if 0 <= new_idx < len(q):
                state.queue_manager.swap_items(idx, new_idx)
                rebuild_queue_ui()

    def rebuild_queue_ui():
        queue_list.controls.clear()
        items = state.queue_manager.get_all()
        for i, item in enumerate(items):
            is_selected = (i == state.selected_queue_index)
            # Use retry handler if we want
            control = DownloadItemControl(item, on_cancel_item, on_remove_item, on_reorder_item, is_selected=is_selected)
            item['control'] = control
            queue_list.controls.append(control.view)
        page.update()

    # Background loop
    def background_loop():
        while True:
            time.sleep(2)
            try:
                process_queue()
            except: pass

            if state.clipboard_monitor_active:
                 try:
                     content = pyperclip.paste()
                     if content and content != state.last_clipboard_content:
                         state.last_clipboard_content = content
                         if validate_url(content):
                             url_input.value = content
                             page.update()
                             page.show_snack_bar(ft.SnackBar(content=ft.Text(f"URL detected: {content}")))
                 except Exception as e:
                     logger.warning(f"Clipboard error: {e}")

    threading.Thread(target=background_loop, daemon=True).start()


if __name__ == "__main__":
    if os.environ.get("FLET_WEB"):
        ft.app(target=main, view=ft.WEB_BROWSER, port=8550)
    else:
        ft.app(target=main)
