import flet as ft
import logging
import threading
import time
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta

from downloader import get_video_info, download_video
from config_manager import ConfigManager
from ui_utils import format_file_size, validate_url, is_ffmpeg_available
from history_manager import HistoryManager
from cloud_manager import CloudManager
from social_manager import SocialManager
from queue_manager import QueueManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

#
# StreamCatch
# Author: Amirreza "Farnam" Taheri
# Contact: taherifarnam@gmail.com
# Github: AmirrezaFarnamTaheri
#

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

        # UX States
        self.selected_queue_index = -1
        self.high_contrast = False
        self.selected_nav_index = 0

        # Try connecting to social
        threading.Thread(target=self.social_manager.connect, daemon=True).start()

state = AppState()

# --- Custom Controls ---

class DownloadItemControl:
    def __init__(self, item: Dict[str, Any], on_cancel: Any, on_remove: Any, on_reorder: Any, is_selected: bool = False):
        self.item = item
        self.on_cancel = on_cancel
        self.on_remove = on_remove
        self.on_reorder = on_reorder
        self.is_selected = is_selected

        self.progress_bar = ft.ProgressBar(value=0, height=8, border_radius=4, color=ft.Colors.BLUE_400, bgcolor=ft.Colors.GREY_800)
        self.status_text = ft.Text(item['status'], size=12, color=ft.Colors.GREY_400)
        self.details_text = ft.Text("Waiting...", size=12, color=ft.Colors.GREY_500)
        self.title_text = ft.Text(
            self.item.get('title', self.item['url']),
            weight=ft.FontWeight.BOLD,
            size=14,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=ft.Colors.WHITE
        )

        self.view = self.build()

    def build(self):
        # Modern Card Design
        bg_color = ft.Colors.GREY_900 if not self.is_selected else ft.Colors.BLUE_GREY_900
        border_color = ft.Colors.TRANSPARENT if not self.is_selected else ft.Colors.BLUE_400

        return ft.Container(
            content=ft.Row([
                # Thumbnail or Icon placeholder
                ft.Container(
                    content=ft.Icon(ft.Icons.VIDEO_FILE, size=30, color=ft.Colors.BLUE_200),
                    width=50, height=50, bgcolor=ft.Colors.BLACK26, border_radius=8,
                    alignment=ft.alignment.center
                ),
                # Info Column
                ft.Expanded(
                    child=ft.Column([
                        self.title_text,
                        self.progress_bar,
                        ft.Row([
                            self.status_text,
                            self.details_text
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ], spacing=5)
                ),
                # Actions
                ft.Column([
                    ft.IconButton(ft.Icons.ARROW_UPWARD, on_click=lambda e: self.on_reorder(self.item, -1), icon_size=18, tooltip="Move Up"),
                    ft.IconButton(ft.Icons.ARROW_DOWNWARD, on_click=lambda e: self.on_reorder(self.item, 1), icon_size=18, tooltip="Move Down"),
                ], spacing=0),
                 ft.Column([
                    ft.IconButton(ft.Icons.CANCEL, on_click=lambda e: self.on_cancel(self.item), icon_size=18, tooltip="Cancel", icon_color=ft.Colors.RED_400),
                    ft.IconButton(ft.Icons.DELETE, on_click=lambda e: self.on_remove(self.item), icon_size=18, tooltip="Remove"),
                ], spacing=0)

            ], spacing=10),
            padding=10,
            bgcolor=bg_color,
            border=ft.border.all(1, border_color),
            border_radius=10,
            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT),
        )

    def update_progress(self):
        self.status_text.value = self.item['status']
        if 'speed' in self.item:
             self.details_text.value = f"{self.item.get('size', '')} • {self.item.get('speed', '')} • ETA: {self.item.get('eta', '')}"
        else:
             self.details_text.value = ""

        self.status_text.update()
        self.details_text.update()
        self.progress_bar.update()
        self.title_text.value = self.item.get('title', self.item['url'])
        self.title_text.update()

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

def main(page: ft.Page):
    page.title = "StreamCatch"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0 # Full bleed
    page.window_min_width = 1100
    page.window_min_height = 800
    page.bgcolor = ft.Colors.BLACK # Deep background

    # --- UI Components ---

    # 1. Navigation Rail (Left Sidebar)
    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.DOWNLOAD, selected_icon=ft.Icons.DOWNLOAD_DONE, label="Download"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.QUEUE_MUSIC, selected_icon=ft.Icons.QUEUE_MUSIC_ROUNDED, label="Queue"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.HISTORY, selected_icon=ft.Icons.HISTORY_TOGGLE_OFF, label="History"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD, selected_icon=ft.Icons.DASHBOARD_CUSTOMIZE, label="Dashboard"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.RSS_FEED, label="RSS"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS, label="Settings"
            ),
        ],
        on_change=lambda e: navigate_to(e.control.selected_index),
    )

    # 2. Content Areas

    # --- Download Tab Content ---
    url_input = ft.TextField(
        label="Video URL",
        hint_text="Paste YouTube, Twitch, or other media links...",
        expand=True,
        border_color=ft.Colors.BLUE_400,
        prefix_icon=ft.Icons.LINK,
        text_size=16
    )

    thumbnail_img = ft.Image(src="", width=400, height=225, fit=ft.ImageFit.COVER, border_radius=10, visible=False)
    title_text = ft.Text("", size=20, weight=ft.FontWeight.BOLD)
    duration_text = ft.Text("", color=ft.Colors.GREY_400)

    video_format_dd = ft.Dropdown(label="Video Quality", options=[], expand=True, border_color=ft.Colors.GREY_700)
    audio_format_dd = ft.Dropdown(label="Audio Format", options=[], expand=True, border_color=ft.Colors.GREY_700)

    # Advanced Options for Download
    playlist_cb = ft.Checkbox(label="Playlist", fill_color=ft.Colors.BLUE_400)
    sponsorblock_cb = ft.Checkbox(label="SponsorBlock", fill_color=ft.Colors.BLUE_400)
    subtitle_dd = ft.Dropdown(label="Subtitles", options=[ft.dropdown.Option("None"), ft.dropdown.Option("en"), ft.dropdown.Option("es")], value="None", width=150, border_color=ft.Colors.GREY_700)

    # New Feature Inputs
    time_start = ft.TextField(label="Start (HH:MM:SS)", width=150, border_color=ft.Colors.GREY_700)
    time_end = ft.TextField(label="End (HH:MM:SS)", width=150, border_color=ft.Colors.GREY_700)
    regex_filter = ft.TextField(label="Playlist Regex Filter", expand=True, border_color=ft.Colors.GREY_700)

    # Batch Import
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
                    _add_url_to_queue(url) # Helper method needed
                    count += 1
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Imported {count} URLs")))
            except Exception as ex:
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Import Error: {ex}")))

    file_picker = ft.FilePicker(on_result=on_file_picker_result)
    page.overlay.append(file_picker)

    batch_btn = ft.OutlinedButton("Batch Import", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: file_picker.pick_files(allow_multiple=False, allowed_extensions=['txt']))

    # Scheduler
    schedule_time_picker = ft.TimePicker(confirm_text="Schedule", error_invalid_text="Time out of range")

    def on_time_picked(e):
        state.scheduled_time = schedule_time_picker.value
        page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Scheduled download for {state.scheduled_time.strftime('%H:%M')}")))

    schedule_time_picker.on_change = on_time_picked
    page.overlay.append(schedule_time_picker)

    schedule_btn = ft.OutlinedButton("Schedule", icon=ft.Icons.SCHEDULE, on_click=lambda _: schedule_time_picker.pick_time())

    download_btn = ft.ElevatedButton(
        "Add to Queue",
        icon=ft.Icons.ADD,
        bgcolor=ft.Colors.BLUE_600,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=20),
        on_click=lambda e: add_to_queue(e)
    )

    fetch_btn = ft.IconButton(ft.Icons.SEARCH, on_click=lambda e: fetch_info_click(e), tooltip="Fetch Info", icon_color=ft.Colors.BLUE_400)

    download_view = ft.Container(
        padding=30,
        content=ft.Column([
            ft.Text("New Download", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(color=ft.Colors.TRANSPARENT, height=20),
            ft.Row([url_input, fetch_btn]),
            ft.Divider(height=30, color=ft.Colors.GREY_900),
            ft.Row([
                # Left: Preview
                ft.Column([
                    ft.Container(
                        content=ft.Stack([
                             ft.Container(bgcolor=ft.Colors.BLACK54, width=400, height=225, border_radius=10), # Placeholder
                             thumbnail_img
                        ]),
                        border_radius=10,
                        border=ft.border.all(1, ft.Colors.GREY_800)
                    ),
                    title_text,
                    duration_text
                ], alignment=ft.MainAxisAlignment.START),

                # Right: Options
                ft.Container(width=20), # Spacer
                ft.Column([
                    ft.Text("Format Options", size=18, weight=ft.FontWeight.W_600),
                    ft.Row([video_format_dd, audio_format_dd]),
                    ft.Divider(height=20, color=ft.Colors.GREY_800),
                    ft.Text("Features", size=18, weight=ft.FontWeight.W_600),
                    ft.Row([playlist_cb, sponsorblock_cb, subtitle_dd]),
                    ft.Row([time_start, time_end]),
                    ft.Row([regex_filter]),
                    ft.Row([batch_btn, schedule_btn]),
                    ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                    download_btn
                ], expand=True)
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
        ], scroll=ft.ScrollMode.AUTO)
    )

    # --- Queue Tab Content ---
    queue_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def clear_queue(e):
        # Remove all non-downloading items
        to_remove = [item for item in state.queue_manager.get_all() if item['status'] != 'Downloading']
        for item in to_remove:
            state.queue_manager.remove_item(item)
        rebuild_queue_ui()

    queue_view = ft.Container(
        padding=30,
        content=ft.Column([
            ft.Row([
                ft.Text("Download Queue", size=28, weight=ft.FontWeight.BOLD),
                ft.OutlinedButton("Clear Queue", icon=ft.Icons.CLEAR_ALL, on_click=clear_queue)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color=ft.Colors.GREY_900),
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
                    border_radius=8,
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400),
                        ft.Column([
                            ft.Text(item.get('title', item['url']), weight=ft.FontWeight.BOLD, overflow=ft.TextOverflow.ELLIPSIS, width=400),
                            ft.Text(f"{item.get('timestamp')} | {item.get('file_size', 'N/A')}", size=12, color=ft.Colors.GREY_500)
                        ]),
                        ft.Spacer(),
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

    history_view = ft.Container(
        padding=30,
        content=ft.Column([
            ft.Row([
                ft.Text("History", size=28, weight=ft.FontWeight.BOLD),
                ft.OutlinedButton("Clear History", icon=ft.Icons.DELETE_SWEEP, on_click=lambda e: clear_history_action())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color=ft.Colors.GREY_900),
            history_list
        ], expand=True)
    )

    def clear_history_action():
        HistoryManager.clear_history()
        load_history()
        page.show_snack_bar(ft.SnackBar(content=ft.Text("History cleared")))

    # --- Dashboard Content ---
    dashboard_view = ft.Container(
        padding=30,
        content=ft.Column([
            ft.Text("Dashboard", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(color=ft.Colors.GREY_900),
            ft.Text("Analytics features coming soon...", color=ft.Colors.GREY_500)
            # Placeholder for now, we can expand if time permits
        ])
    )

    # --- RSS Content ---
    rss_input = ft.TextField(label="Feed URL", expand=True, border_color=ft.Colors.GREY_700)
    rss_list_view = ft.ListView(expand=True)

    def load_rss_feeds():
        rss_list_view.controls.clear()
        for feed in state.config.get('rss_feeds', []):
            rss_list_view.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.RSS_FEED, color=ft.Colors.ORANGE_400),
                    title=ft.Text(feed),
                    trailing=ft.IconButton(ft.Icons.DELETE, on_click=lambda e, f=feed: remove_rss(f))
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
        padding=30,
        content=ft.Column([
            ft.Text("RSS Manager", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(color=ft.Colors.GREY_900),
            ft.Row([rss_input, ft.IconButton(ft.Icons.ADD_CIRCLE, on_click=add_rss, icon_size=40, icon_color=ft.Colors.BLUE_400)]),
            rss_list_view
        ], expand=True)
    )

    # --- Settings Content ---
    proxy_input = ft.TextField(label="Proxy", value=state.config.get('proxy', ''), border_color=ft.Colors.GREY_700)
    rate_limit_input = ft.TextField(label="Rate Limit (e.g. 5M)", value=state.config.get('rate_limit', ''), border_color=ft.Colors.GREY_700)
    output_template_input = ft.TextField(label="Output Template", value=state.config.get('output_template', '%(title)s.%(ext)s'), border_color=ft.Colors.GREY_700)
    use_aria2c_cb = ft.Checkbox(label="Use Aria2c Accelerator", value=state.config.get('use_aria2c', False))
    gpu_accel_dd = ft.Dropdown(label="GPU Acceleration", options=[
        ft.dropdown.Option("None"), ft.dropdown.Option("auto"), ft.dropdown.Option("cuda"), ft.dropdown.Option("vulkan")
    ], value=state.config.get('gpu_accel', 'None'), border_color=ft.Colors.GREY_700)

    def save_settings(e):
        state.config['proxy'] = proxy_input.value
        state.config['rate_limit'] = rate_limit_input.value
        state.config['output_template'] = output_template_input.value
        state.config['use_aria2c'] = use_aria2c_cb.value
        state.config['gpu_accel'] = gpu_accel_dd.value
        ConfigManager.save_config(state.config)
        page.show_snack_bar(ft.SnackBar(content=ft.Text("Settings saved successfully!")))

    settings_view = ft.Container(
        padding=30,
        content=ft.Column([
            ft.Text("Settings", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(color=ft.Colors.GREY_900),
            proxy_input,
            rate_limit_input,
            output_template_input,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Text("Performance", size=18, weight=ft.FontWeight.W_600),
            use_aria2c_cb,
            gpu_accel_dd,
            ft.Divider(height=20, color=ft.Colors.GREY_800),
            ft.ElevatedButton("Save Configuration", on_click=save_settings, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)
        ], scroll=ft.ScrollMode.AUTO)
    )

    # --- Layout Assembly ---

    content_area = ft.Container(expand=True, bgcolor=ft.Colors.BLACK)

    views = [
        download_view,
        queue_view,
        history_view,
        dashboard_view,
        rss_view,
        settings_view
    ]

    def navigate_to(index):
        state.selected_nav_index = index
        content_area.content = views[index]
        if index == 2: # History
            load_history()
        if index == 4: # RSS
            load_rss_feeds()
        page.update()

    # Initial View
    content_area.content = views[0]

    layout = ft.Row([
        nav_rail,
        ft.VerticalDivider(width=1, color=ft.Colors.GREY_900),
        content_area
    ], expand=True, spacing=0)

    # Cinema Mode Overlay
    cinema_overlay = ft.Container(
        visible=False, expand=True, bgcolor=ft.Colors.BLACK, alignment=ft.alignment.center,
        content=ft.Column([
             ft.Icon(ft.Icons.MOVIE, size=50, color=ft.Colors.BLUE_400),
             ft.Text("Cinema Mode", size=30, weight=ft.FontWeight.BOLD),
             ft.ProgressBar(width=500, color=ft.Colors.BLUE_400, bgcolor=ft.Colors.GREY_800),
             ft.Text("Downloading...", color=ft.Colors.GREY_400),
             ft.OutlinedButton("Exit", on_click=lambda e: toggle_cinema_mode(False))
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    page.add(ft.Stack([layout, cinema_overlay], expand=True))


    # --- Logic Implementation ---

    def toggle_cinema_mode(enable):
        state.cinema_mode = enable
        cinema_overlay.visible = enable
        page.update()

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

            # Update UI via main thread mostly? Flet is thread-safe for property updates usually
            thumbnail_img.src = info.get('thumbnail') or ""
            thumbnail_img.visible = True
            title_text.value = info.get('title', 'N/A')
            duration_text.value = info.get('duration', '')

            # Dropdowns
            video_opts = [ft.dropdown.Option(key=s['format_id'], text=f"{s['resolution']} ({s['ext']})") for s in info.get('video_streams', [])]
            video_format_dd.options = video_opts
            if video_opts: video_format_dd.value = video_opts[0].key

            audio_opts = [ft.dropdown.Option(key=s['format_id'], text=f"{s['abr']}kbps ({s['ext']})") for s in info.get('audio_streams', [])]
            audio_format_dd.options = audio_opts
            if audio_opts: audio_format_dd.value = audio_opts[0].key

            page.show_snack_bar(ft.SnackBar(content=ft.Text("Metadata fetched successfully")))

        except Exception as e:
            logger.error(f"Fetch error: {e}")
            page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Error: {e}")))
        finally:
            fetch_btn.disabled = False
            page.update()

    def _add_url_to_queue(url_val, custom_title=None):
        # Helper to add item
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
            "title": custom_title or (state.video_info.get('title', 'Unknown') if url_val == url_input.value else url_val),
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
            "match_filter": regex_filter.value
        }
        state.queue_manager.add_item(item)

    def add_to_queue(e):
        if not state.video_info:
            page.show_snack_bar(ft.SnackBar(content=ft.Text("Please fetch video info first!")))
            return

        _add_url_to_queue(url_input.value)

        # Reset one-time use fields if needed, or keep them. Keeping for UX.
        # Reset scheduled time after adding to avoid persistent scheduling
        state.scheduled_time = None

        rebuild_queue_ui()
        page.show_snack_bar(ft.SnackBar(content=ft.Text("Added to queue")))

        # Auto-start if queue was empty/idle
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
            # Create control if not exists or recreate to refresh
            control = DownloadItemControl(item, on_cancel_item, on_remove_item, on_reorder_item, is_selected)
            item['control'] = control
            queue_list.controls.append(control.view)
        page.update()

    def process_queue():
        # Check for scheduled items
        items = state.queue_manager.get_all()
        now = datetime.now()
        for item in items:
            if item.get('scheduled_time') and item['status'].startswith("Scheduled"):
                if now >= item['scheduled_time']:
                     item['status'] = 'Queued'
                     item['scheduled_time'] = None
                     # Notify UI update needed? Queue UI updates on re-render or we can trigger it
                     # If we are in a background thread, we can't easily update UI directly without page reference
                     pass

        if state.queue_manager.any_downloading(): return

        item = state.queue_manager.find_next_downloadable()
        if item:
             threading.Thread(target=download_task, args=(item,), daemon=True).start()

    # Background scheduler check
    def scheduler_loop():
        while True:
            time.sleep(10)
            try:
                process_queue()
            except: pass

    threading.Thread(target=scheduler_loop, daemon=True).start()

    def download_task(item):
        item['status'] = 'Downloading'
        state.current_download_item = item
        state.cancel_token = CancelToken()

        if 'control' in item: item['control'].update_progress()

        try:
            def progress_hook(d, _):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        pct = downloaded / total
                        if 'control' in item:
                            item['control'].progress_bar.value = pct

                        if state.cinema_mode:
                            cinema_overlay.content.controls[2].value = pct
                            cinema_overlay.content.controls[3].value = f"Downloading {int(pct*100)}%"
                            cinema_overlay.update()

                    item['speed'] = format_file_size(d.get('speed', 0)) + "/s"
                    item['size'] = format_file_size(total)
                    item['eta'] = f"{d.get('eta', 0)}s"

                    if 'control' in item: item['control'].update_progress()

                elif d['status'] == 'finished':
                    item['status'] = 'Processing'
                    if 'control' in item:
                        item['control'].progress_bar.value = 1.0
                        item['control'].update_progress()

                    # Save filename for history
                    item['final_filename'] = d.get('filename')

            download_video(
                item['url'],
                progress_hook,
                item,
                video_format=item.get('video_format', 'best'),
                output_path=item.get('output_path'),
                cancel_token=state.cancel_token,
                sponsorblock_remove=item.get('sponsorblock', False),
                playlist=item.get('playlist', False),
                use_aria2c=item.get('use_aria2c', False),
                gpu_accel=item.get('gpu_accel'),
                output_template=item.get('output_template'),
                start_time=item.get('start_time'),
                end_time=item.get('end_time'),
                match_filter=item.get('match_filter')
            )

            item['status'] = 'Completed'

            # History Integration
            HistoryManager.add_entry(
                url=item['url'],
                title=item.get('title', 'Unknown'),
                output_path=item.get('output_path'),
                format_str=item.get('video_format'),
                status='Completed',
                file_size=item.get('size', 'N/A'),
                file_path=item.get('final_filename')
            )

        except Exception as e:
            if "cancelled" in str(e):
                item['status'] = 'Cancelled'
            else:
                item['status'] = 'Error'
                logger.error(f"Download failed: {e}")
        finally:
            if 'control' in item: item['control'].update_progress()
            state.current_download_item = None
            state.cancel_token = None
            process_queue()


if __name__ == "__main__":
    if os.environ.get("FLET_WEB"):
        ft.app(target=main, view=ft.WEB_BROWSER, port=8550)
    else:
        ft.app(target=main)
