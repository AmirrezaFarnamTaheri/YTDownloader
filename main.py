import flet as ft
import logging
import threading
import time
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import queue
from datetime import datetime, timedelta
import math

from downloader import get_video_info, download_video
from config_manager import ConfigManager
from ui_utils import format_file_size, validate_url, is_ffmpeg_available
from history_manager import HistoryManager
from cloud_manager import CloudManager
from social_manager import SocialManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- State Management ---
class AppState:
    def __init__(self):
        self.config = ConfigManager.load_config()
        self.download_queue: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []
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
        self.selected_queue_index = -1 # For keyboard navigation
        self.high_contrast = False

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
        self.progress_bar = ft.ProgressBar(value=0, width=300)
        self.status_text = ft.Text(item['status'], tooltip=f"Status: {item['status']}")
        self.details_text = ft.Text("Waiting...", tooltip="Download details")
        self.view = self.build()

    def build(self):
        # Determine background color based on selection and theme
        if state.high_contrast:
            bg_color = ft.Colors.WHITE if self.is_selected else ft.Colors.BLACK
            text_color = ft.Colors.BLACK if self.is_selected else ft.Colors.WHITE
        else:
            bg_color = ft.Colors.BLUE_GREY_900 if self.is_selected else "#2b2b2b" # Match surface variant
            text_color = None # Default

        return ft.Card(
            color=bg_color,
            content=ft.Container(
                padding=10,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.DRAG_HANDLE, color=text_color or ft.Colors.GREY),
                        ft.Text(
                            self.item['url'],
                            weight=ft.FontWeight.BOLD,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            width=250,
                            color=text_color,
                            tooltip=f"URL: {self.item['url']}"
                        ),
                        ft.Row([
                             ft.IconButton(ft.Icons.ARROW_UPWARD, on_click=lambda e: self.on_reorder(self.item, -1), tooltip="Move Up", icon_size=16, icon_color=text_color),
                             ft.IconButton(ft.Icons.ARROW_DOWNWARD, on_click=lambda e: self.on_reorder(self.item, 1), tooltip="Move Down", icon_size=16, icon_color=text_color),
                        ]),
                        ft.IconButton(ft.Icons.CANCEL, on_click=lambda e: self.on_cancel(self.item), tooltip="Cancel", icon_color=text_color),
                        ft.IconButton(ft.Icons.DELETE, on_click=lambda e: self.on_remove(self.item), tooltip="Remove", icon_color=text_color)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.status_text,
                    self.progress_bar,
                    self.details_text
                ])
            )
        )

    def update_progress(self):
        self.status_text.value = self.item['status']
        self.details_text.value = f"{self.item.get('size', 'N/A')} | {self.item.get('speed', 'N/A')} | ETA: {self.item.get('eta', 'N/A')}"
        self.status_text.update()
        self.details_text.update()
        self.progress_bar.update()

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
    page.title = "StreamCatch - Modern Media Downloader"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window_min_width = 1000
    page.window_min_height = 700

    # Accessibility Semantics
    page.semantics_mode = True

    # Create Logo SVG file if not exists (in case asset folder was missed)
    assets_dir = Path(__file__).parent / "assets"
    assets_dir.mkdir(exist_ok=True)
    logo_path = assets_dir / "logo.svg"
    if not logo_path.exists():
        # Simplified fallback
        try:
            # Create a simple placeholder SVG
            with open(logo_path, 'w', encoding='utf-8') as f:
                f.write('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"><circle cx="20" cy="20" r="18" stroke="blue" stroke-width="4" fill="lightblue" /><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="white" font-size="20">SC</text></svg>')
        except Exception as e:
            logger.warning(f"Failed to create fallback logo: {e}")

    # --- UI Elements ---

    # Cinema Mode Overlay
    cinema_overlay = ft.Container(
        visible=False,
        expand=True,
        bgcolor=ft.Colors.BLACK,
        alignment=ft.alignment.center,
        content=ft.Column(
            controls=[
                ft.Text("Cinema Mode", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.ProgressBar(width=400, color=ft.Colors.BLUE), # Global Progress
                ft.Text("Downloading...", color=ft.Colors.WHITE70),
                ft.ElevatedButton("Exit Cinema Mode", on_click=lambda e: toggle_cinema_mode(e))
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

    # Header
    theme_icon = ft.IconButton(ft.Icons.DARK_MODE, on_click=lambda e: toggle_theme(e), tooltip="Toggle Dark/Light Theme")
    high_contrast_btn = ft.IconButton(ft.Icons.CONTRAST, tooltip="High Contrast Mode", on_click=lambda e: toggle_high_contrast(e))
    cinema_btn = ft.IconButton(ft.Icons.FULLSCREEN, tooltip="Cinema Mode", on_click=lambda e: toggle_cinema_mode(e))

    # Logo
    logo_img = ft.Image(src="assets/logo.svg", width=40, height=40, tooltip="StreamCatch Logo")

    header = ft.Row([
        ft.Row([logo_img, ft.Text("StreamCatch", size=24, weight=ft.FontWeight.BOLD)]),
        ft.Row([cinema_btn, high_contrast_btn, theme_icon])
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # URL Input
    url_input = ft.TextField(label="Paste Video URL", expand=True)

    def fetch_info_click(e):
        if not url_input.value:
            page.show_snack_bar(ft.SnackBar(content=ft.Text("Please enter a URL")))
            return
        
        fetch_btn.disabled = True
        page.update()
        
        # Run in thread
        threading.Thread(target=fetch_info_task, args=(url_input.value,), daemon=True).start()

    fetch_btn = ft.ElevatedButton("Fetch Info", on_click=fetch_info_click, tooltip="Fetch video metadata")

    async def paste_url(e):
        val = await page.get_clipboard()
        if val:
            url_input.value = val
            page.update()

    input_row = ft.Row([
        url_input,
        ft.IconButton(ft.Icons.PASTE, on_click=paste_url, tooltip="Paste URL"),
        fetch_btn
    ])

    # Preview Section
    thumbnail_img = ft.Image(src="", width=320, height=180, fit=ft.ImageFit.COVER, visible=False, tooltip="Video Thumbnail")
    title_text = ft.Text("No video loaded", size=16, weight=ft.FontWeight.BOLD)
    duration_text = ft.Text("Duration: --:--")

    preview_col = ft.Column([
        thumbnail_img,
        title_text,
        duration_text
    ], alignment=ft.MainAxisAlignment.START)

    # Tabs
    # Video Tab
    video_format_dd = ft.Dropdown(label="Video Quality", options=[], expand=True)

    # Audio Tab
    audio_format_dd = ft.Dropdown(label="Audio Format", options=[], expand=True)
    visualizer_placeholder = ft.Container(
        content=ft.Text("Visualizer Placeholder (Real-time spectrum)", color=ft.Colors.WHITE54),
        height=100, width=300, bgcolor=ft.Colors.BLACK12, alignment=ft.alignment.center,
        border_radius=5
    )

    # Advanced Tab
    sponsorblock_cb = ft.Checkbox(label="Enable SponsorBlock (Skip Segments)")
    playlist_cb = ft.Checkbox(label="Download Playlist")
    subtitle_dd = ft.Dropdown(label="Subtitles", options=[ft.dropdown.Option("None"), ft.dropdown.Option("en"), ft.dropdown.Option("es")], value="None")

    # Performance options (Placeholder UI for now, logic in downloader.py)
    use_aria2c_cb = ft.Checkbox(label="Use Aria2c Accelerator (Multi-threaded)", value=state.config.get('use_aria2c', False))
    gpu_accel_dd = ft.Dropdown(label="GPU Acceleration", options=[
        ft.dropdown.Option("None"),
        ft.dropdown.Option("auto"),
        ft.dropdown.Option("cuda"),
        ft.dropdown.Option("vulkan")
    ], value=state.config.get('gpu_accel', 'None'))

    # Time Range
    time_start = ft.TextField(label="Start (HH:MM:SS)", width=100)
    time_end = ft.TextField(label="End (HH:MM:SS)", width=100)

    # Regex Filter
    regex_filter = ft.TextField(label="Regex Filter (Playlist)", hint_text="e.g. ^Lecture \\d+", expand=True)

    # Batch Import Logic
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

                # Add all to queue
                for url in valid_urls:
                    _add_item_to_queue(url)

                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Imported {len(valid_urls)} URLs")))

            except Exception as ex:
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Error importing: {str(ex)}")))

    file_picker = ft.FilePicker(on_result=on_file_picker_result)
    page.overlay.append(file_picker)

    def import_batch(e):
        file_picker.pick_files(allow_multiple=False, allowed_extensions=['txt'])

    batch_btn = ft.ElevatedButton("Import Batch", on_click=import_batch)

    # Scheduler Logic
    def on_time_picker_change(e):
        if time_picker.value:
            state.scheduled_time = time_picker.value
            page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Scheduled for {state.scheduled_time.strftime('%H:%M')}")))
            schedule_btn.text = f"Scheduled @ {state.scheduled_time.strftime('%H:%M')}"
            page.update()

    time_picker = ft.TimePicker(on_change=on_time_picker_change)
    page.overlay.append(time_picker)

    def schedule_download(e):
        time_picker.pick_time()

    schedule_btn = ft.ElevatedButton("Schedule", on_click=schedule_download)

    # Settings Tab
    proxy_input = ft.TextField(label="Proxy", hint_text="http://user:pass@host:port", value=state.config.get('proxy', ''))
    rate_limit_input = ft.TextField(label="Rate Limit", hint_text="e.g. 5M", value=state.config.get('rate_limit', ''))
    output_template_input = ft.TextField(label="Output Template", hint_text="%(title)s.%(ext)s", value=state.config.get('output_template', ''))

    def export_data(e):
        try:
            from sync_manager import SyncManager
            path = SyncManager.export_data()
            page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Data exported to {path}")))
        except Exception as ex:
             page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Export failed: {ex}")))

    def import_data(e):
        try:
            from sync_manager import SyncManager
            SyncManager.import_data()
            page.show_snack_bar(ft.SnackBar(content=ft.Text("Data imported. Please restart.")))
        except Exception as ex:
             page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Import failed: {ex}")))

    export_btn = ft.ElevatedButton("Export Data", on_click=export_data)
    import_btn = ft.ElevatedButton("Import Data", on_click=import_data)

    def save_settings(e):
        state.config['proxy'] = proxy_input.value
        state.config['rate_limit'] = rate_limit_input.value
        state.config['output_template'] = output_template_input.value
        state.config['use_aria2c'] = use_aria2c_cb.value
        state.config['gpu_accel'] = gpu_accel_dd.value
        ConfigManager.save_config(state.config)
        page.show_snack_bar(ft.SnackBar(content=ft.Text("Settings saved")))

    save_settings_btn = ft.ElevatedButton("Save Settings", on_click=save_settings)

    # RSS Tab
    rss_input = ft.TextField(label="RSS Feed URL", expand=True)
    rss_list = ft.ListView(expand=True, height=200, spacing=5)

    def load_rss_feeds():
        rss_list.controls.clear()
        for feed in state.config.get('rss_feeds', []):
            rss_list.controls.append(
                ft.ListTile(
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

    load_rss_feeds()

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="Video", content=ft.Container(content=ft.Column([video_format_dd, playlist_cb]), padding=10)),
            ft.Tab(text="Audio", content=ft.Container(content=ft.Column([audio_format_dd, visualizer_placeholder]), padding=10)),
            ft.Tab(text="Advanced", content=ft.Container(content=ft.Column([
                sponsorblock_cb,
                subtitle_dd,
                ft.Row([time_start, time_end]),
                regex_filter,
                ft.Divider(),
                ft.Row([batch_btn, schedule_btn])
            ]), padding=10)),
            ft.Tab(text="Settings", content=ft.Container(content=ft.Column([
                proxy_input,
                rate_limit_input,
                output_template_input,
                ft.Text("Performance", weight=ft.FontWeight.BOLD),
                use_aria2c_cb,
                gpu_accel_dd,
                ft.Divider(),
                save_settings_btn,
                ft.Divider(),
                ft.Row([export_btn, import_btn])
            ]), padding=10)),
             ft.Tab(text="RSS", content=ft.Container(content=ft.Column([
                ft.Row([rss_input, ft.IconButton(ft.Icons.ADD, on_click=add_rss)]),
                ft.Text("Subscribed Feeds:", weight=ft.FontWeight.BOLD),
                rss_list
            ]), padding=10)),
        ],
        expand=True,
    )

    # Queue Section
    queue_list = ft.ListView(expand=True, spacing=10, padding=20, auto_scroll=False) # Auto scroll conflicts with nav?

    # History Section
    history_list = ft.ListView(expand=True, spacing=10, padding=20)

    # Dashboard Section
    def get_dashboard_data():
        history = HistoryManager.get_history(limit=1000)
        total_downloads = len(history)
        
        return ft.Column([
            ft.Text("Dashboard Analytics", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Card(content=ft.Container(padding=20, content=ft.Column([ft.Text("Total Downloads"), ft.Text(str(total_downloads), size=30)]))),
                ft.Card(content=ft.Container(padding=20, content=ft.Column([ft.Text("History Items"), ft.Text(str(len(history)), size=30)]))),
            ]),
            ft.Text("Downloads Activity", size=16),
            ft.BarChart(
                bar_groups=[
                    ft.BarChartGroup(x=0, bar_rods=[ft.BarChartRod(from_y=0, to_y=total_downloads, width=40, color=ft.Colors.BLUE, tooltip="Total", border_radius=0)]),
                ],
                border=ft.border.all(1, "#BDBDBD"), # GREY_400 hex
                left_axis=ft.ChartAxis(labels_size=40, title=ft.Text("Downloads"), title_size=40),
                bottom_axis=ft.ChartAxis(labels_size=40, title=ft.Text("Total"), title_size=40),
                horizontal_grid_lines=ft.ChartGridLines(color="#E0E0E0", width=1, dash_pattern=[3, 3]), # GREY_300 hex
                tooltip_bgcolor="#80E0E0E0", # Semi-transparent GREY_300 approx
                interactive=True,
                expand=True,
            )
        ])

    dashboard_content = get_dashboard_data()

    # Main Layout (Split View)
    # Left: Preview + Options
    left_panel = ft.Container(
        content=ft.Column([
            preview_col,
            tabs
        ]),
        width=400,
        padding=10,
        bgcolor="#2b2b2b", # Surface Variant approximation
        border_radius=10,
    )

    # Right: Queue / History / Dashboard
    right_tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Queue", content=queue_list),
            ft.Tab(text="History", content=history_list),
            ft.Tab(text="Dashboard", content=ft.Container(content=dashboard_content, padding=10)),
        ],
        expand=True
    )

    right_panel = ft.Container(
        content=right_tabs,
        expand=True,
        padding=10,
        bgcolor="#2b2b2b", # Surface Variant approximation
        border_radius=10,
    )

    content_row = ft.Row([left_panel, right_panel], expand=True, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)

    # Bottom Bar
    status_text = ft.Text("Ready")

    # Cloud / Social Placeholders
    cloud_icon = ft.Icon(ft.Icons.CLOUD_UPLOAD, tooltip="Auto-upload enabled (Mock)")
    share_icon = ft.Icon(ft.Icons.SHARE, tooltip="Share active")

    download_btn = ft.ElevatedButton("Add to Queue", on_click=lambda e: add_to_queue(e))

    bottom_bar = ft.Container(
        content=ft.Row([
            ft.Row([status_text, cloud_icon, share_icon]),
            download_btn
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=10,
        bgcolor="#121212", # Background hex
    )

    # Wrapper stack to handle Cinema Mode Overlay
    main_stack = ft.Stack([
        ft.Column([
            header,
            ft.Divider(),
            input_row,
            content_row,
            bottom_bar
        ], expand=True),
        cinema_overlay
    ], expand=True)

    # --- Logic Functions ---

    def toggle_theme(e):
        page.theme_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        theme_icon.icon = ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE
        page.update()

    def toggle_high_contrast(e):
        state.high_contrast = not state.high_contrast
        # Re-apply theme colors manually if needed or just trigger redraw
        # Flet doesn't have a built-in High Contrast theme mode, so we toggle custom logic
        page.show_snack_bar(ft.SnackBar(content=ft.Text(f"High Contrast: {'ON' if state.high_contrast else 'OFF'}")))
        rebuild_queue_ui()

    def toggle_cinema_mode(e):
        state.cinema_mode = not state.cinema_mode
        cinema_overlay.visible = state.cinema_mode
        page.update()

    def handle_keyboard(e: ft.KeyboardEvent):
        # Simple queue navigation
        if not state.download_queue: return

        # Avoid capturing if typing in text field?
        # Flet doesn't easily expose focused control type, so we rely on users clicking out or using shortcuts

        if e.key == "J": # Down
            state.selected_queue_index += 1
            if state.selected_queue_index >= len(state.download_queue):
                state.selected_queue_index = 0
            rebuild_queue_ui()

        elif e.key == "K": # Up
            state.selected_queue_index -= 1
            if state.selected_queue_index < 0:
                state.selected_queue_index = len(state.download_queue) - 1
            rebuild_queue_ui()

        elif e.key == "D": # Delete
            if 0 <= state.selected_queue_index < len(state.download_queue):
                item = state.download_queue[state.selected_queue_index]
                on_remove_item(item)
                # Adjust index
                state.selected_queue_index = max(0, state.selected_queue_index - 1)
                rebuild_queue_ui()

        elif e.key == " ": # Pause/Resume
            # Toggle global pause or specific item?
            # Let's toggle global pause for now as per user request "Pause all" or similar context
            # Actually request says "Space to pause".
            # We will toggle the cancel token pause if active
            if state.cancel_token:
                if state.cancel_token.is_paused:
                    state.cancel_token.resume()
                    page.show_snack_bar(ft.SnackBar(content=ft.Text("Resumed")))
                else:
                    state.cancel_token.pause()
                    page.show_snack_bar(ft.SnackBar(content=ft.Text("Paused")))

    page.on_keyboard_event = handle_keyboard

    def fetch_info_task(url):
        try:
            info = get_video_info(url)
            if not info: raise Exception("Failed to fetch info")

            state.video_info = info

            # Update UI
            title_text.value = info.get('title', 'N/A')
            duration_text.value = f"Duration: {info.get('duration', 'N/A')}"

            if info.get('thumbnail'):
                thumbnail_img.src = info.get('thumbnail')
                thumbnail_img.visible = True

            # Update Dropdowns
            video_opts = []
            for s in info.get('video_streams', []):
                label = f"{s.get('resolution')} ({s.get('ext')})"
                video_opts.append(ft.dropdown.Option(key=s.get('format_id'), text=label))
            video_format_dd.options = video_opts
            if video_opts: video_format_dd.value = video_opts[0].key

            audio_opts = []
            for s in info.get('audio_streams', []):
                label = f"{s.get('abr')}kbps ({s.get('ext')})"
                audio_opts.append(ft.dropdown.Option(key=s.get('format_id'), text=label))
            audio_format_dd.options = audio_opts
            if audio_opts: audio_format_dd.value = audio_opts[0].key

            status_text.value = "Video info loaded."
        except Exception as e:
            status_text.value = f"Error: {str(e)}"
        finally:
            fetch_btn.disabled = False
            page.update()

    def _add_item_to_queue(url):
        status = "Queued"
        sched_dt = None
        
        # Time Validation
        start_val = time_start.value.strip() if time_start.value else None
        end_val = time_end.value.strip() if time_end.value else None

        import re
        time_pattern = r'^(\d{1,2}:)?\d{1,2}:\d{2}$'
        if start_val and not re.match(time_pattern, start_val):
             page.show_snack_bar(ft.SnackBar(content=ft.Text("Invalid Start Time format (HH:MM:SS or MM:SS)")))
             return
        if end_val and not re.match(time_pattern, end_val):
             page.show_snack_bar(ft.SnackBar(content=ft.Text("Invalid End Time format (HH:MM:SS or MM:SS)")))
             return

        if state.scheduled_time:
             now = datetime.now()
             sched_dt = datetime.combine(now.date(), state.scheduled_time)
             if sched_dt < now:
                 sched_dt += timedelta(days=1)
             status = f"Scheduled ({sched_dt.strftime('%H:%M')})"

        item = {
            "url": url,
            "status": status,
            "scheduled_time": sched_dt,
            "video_format": video_format_dd.value,
            "output_path": str(Path.home() / "Downloads"),
            "playlist": playlist_cb.value,
            "sponsorblock": sponsorblock_cb.value,
            "start_time": start_val,
            "end_time": end_val,
            "match_filter": regex_filter.value if regex_filter.value else None,
            "output_template": output_template_input.value if output_template_input.value else None,
            "use_aria2c": use_aria2c_cb.value,
            "gpu_accel": gpu_accel_dd.value
        }
        state.download_queue.append(item)
        
        # Check if this is the first item, select it
        if len(state.download_queue) == 1:
            state.selected_queue_index = 0

        is_selected = (state.download_queue.index(item) == state.selected_queue_index)
        item_control = DownloadItemControl(item, on_cancel_item, on_remove_item, on_reorder_item, is_selected=is_selected)
        item['control'] = item_control
        queue_list.controls.append(item_control.view)
        page.update()
        
        if not sched_dt:
            process_queue()

    def add_to_queue(e):
        if not state.video_info:
            page.show_snack_bar(ft.SnackBar(content=ft.Text("Fetch video info first")))
            return
        _add_item_to_queue(url_input.value)

    def on_cancel_item(item):
        item['status'] = 'Cancelled'
        if state.current_download_item == item and state.cancel_token:
            state.cancel_token.cancel()
        if 'control' in item:
            item['control'].update_progress()

    def on_remove_item(item):
        if item in state.download_queue:
            state.download_queue.remove(item)
            rebuild_queue_ui()

    def on_reorder_item(item, direction):
        """Move item up (-1) or down (1) in the queue."""
        if item not in state.download_queue: return
        
        idx = state.download_queue.index(item)
        new_idx = idx + direction

        if 0 <= new_idx < len(state.download_queue):
            state.download_queue[idx], state.download_queue[new_idx] = state.download_queue[new_idx], state.download_queue[idx]
            rebuild_queue_ui()

    def rebuild_queue_ui():
        queue_list.controls.clear()
        for i, q_item in enumerate(state.download_queue):
            # Update selection state in control
            is_selected = (i == state.selected_queue_index)
            # We need to recreate the control to update style or add a method to update style
            # Recreating is easier for now
            q_item['control'] = DownloadItemControl(q_item, on_cancel_item, on_remove_item, on_reorder_item, is_selected=is_selected)
            queue_list.controls.append(q_item['control'].view)
        page.update()

    def process_queue():
        if any(i['status'] == 'Downloading' for i in state.download_queue): return

        # Check scheduled items
        now = datetime.now()
        for item in state.download_queue:
            if item.get('scheduled_time') and item['status'].startswith("Scheduled"):
                if now >= item['scheduled_time']:
                    item['status'] = 'Queued'
                    item['scheduled_time'] = None
                    item['control'].update_progress()

        for item in state.download_queue:
            if item['status'] == 'Queued':
                threading.Thread(target=download_task, args=(item,), daemon=True).start()
                break

        # Schedule next check if there are scheduled items
        if any(i['status'].startswith("Scheduled") for i in state.download_queue):
             # We can't easily loop here without blocking, but we can use page.run_task or threading
             # Simpler: Flet page.on_tick? No.
             # We'll rely on the periodic check from a background thread or just check when queue frees up.
             # Ideally we start a background monitor.
             pass

    def background_scheduler_monitor():
        while True:
            time.sleep(5)
            try:
                need_update = False
                now = datetime.now()
                for item in state.download_queue:
                    if item.get('scheduled_time') and item['status'].startswith("Scheduled"):
                         if now >= item['scheduled_time']:
                             item['status'] = 'Queued'
                             item['scheduled_time'] = None
                             need_update = True

                if need_update:
                    process_queue()
            except: pass

    # Start scheduler monitor in a thread, but only if not in test mode to avoid lingering threads
    if not os.environ.get("TEST_MODE"):
        threading.Thread(target=background_scheduler_monitor, daemon=True).start()

    def download_task(item):
        item['status'] = 'Downloading'
        state.current_download_item = item
        state.cancel_token = CancelToken()

        if 'control' in item and item['control']:
             item['control'].update_progress()

        try:
            def progress_hook(d, _):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        pct = (downloaded / total)
                        if 'control' in item and item['control']:
                            item['control'].progress_bar.value = pct
                        if state.cinema_mode:
                            # Update cinema mode progress
                             cinema_overlay.content.controls[1].value = pct
                             cinema_overlay.content.controls[2].value = f"Downloading {item['url']}... {int(pct*100)}%"
                             cinema_overlay.update()

                    # Social Update (Rate limit handled in manager implicitly or add throttle here)
                    # We'll do it every 5% or so to avoid spamming RPC
                    if int(pct * 100) % 5 == 0:
                        state.social_manager.update_status(
                            state="Downloading",
                            details=f"{item.get('title', 'Video')} - {int(pct*100)}%"
                        )

                    item['size'] = format_file_size(total)
                    item['speed'] = format_file_size(d.get('speed', 0)) + "/s"
                    item['eta'] = f"{int(d.get('eta', 0))}s"
                    if 'control' in item and item['control']:
                        item['control'].update_progress()

                elif d['status'] == 'finished':
                    if 'control' in item and item['control']:
                        item['control'].progress_bar.value = 1.0
                        item['control'].update_progress()
                    item['status'] = 'Processing'
                    # Capture filename for cloud upload
                    if 'filename' in d:
                        item['final_filename'] = d['filename']

            download_video(
                item['url'],
                progress_hook,
                item,
                video_format=item.get('video_format', 'best'),
                output_path=item.get('output_path'),
                cancel_token=state.cancel_token,
                sponsorblock_remove=item.get('sponsorblock', False),
                playlist=item.get('playlist', False),
                start_time=item.get('start_time'),
                end_time=item.get('end_time'),
                match_filter=item.get('match_filter'),
                output_template=item.get('output_template'),
                use_aria2c=item.get('use_aria2c', False),
                gpu_accel=item.get('gpu_accel')
            )
            item['status'] = 'Completed'

            state.social_manager.update_status(state="Idle", details="Ready to download")

            # Cloud Upload
            try:
                item['status'] = 'Uploading...'
                if 'control' in item and item['control']:
                    item['control'].update_progress()
                state.cloud_manager.upload_file(item.get('final_filename', item.get('output_path')))
                item['status'] = 'Uploaded'
            except Exception as e:
                if "not configured" in str(e):
                     item['status'] = 'Completed (Upload Skipped)'
                else:
                     logger.error(f"Upload failed: {e}")
                     item['status'] = 'Completed (Upload Failed)'

        except Exception as e:
            if "cancelled" in str(e):
                item['status'] = 'Cancelled'
            else:
                item['status'] = 'Error'
                # Show error details in details_text indirectly by updating status or creating a way to see it
                # For now, we'll append it to status if it's short, or log it
                logger.error(f"Download error: {e}")
                if 'control' in item and item['control']:
                     item['control'].details_text.value = f"Error: {str(e)[:50]}..."
        finally:
            if 'control' in item and item['control']:
                item['control'].update_progress()
            state.current_download_item = None
            state.cancel_token = None
            if state.cinema_mode:
                cinema_overlay.content.controls[1].value = 0
                cinema_overlay.content.controls[2].value = "Ready"
                cinema_overlay.update()
            process_queue()

    # Assemble Page
    page.add(main_stack)

if __name__ == "__main__":
    if os.environ.get("FLET_WEB"):
        ft.app(target=main, view=ft.WEB_BROWSER, port=8550)
    else:
        ft.app(target=main)
