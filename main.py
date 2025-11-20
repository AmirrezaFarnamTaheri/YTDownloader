import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import sys
import datetime

# Try to initialise Tk to determine if a display is available.
try:  # pragma: no cover - exercised implicitly in tests
    _test_root = tk.Tk()
    _test_root.destroy()
    tk._ytdownloader_headless = False  # type: ignore[attr-defined]
except tk.TclError:  # pragma: no cover - covered by integration tests
    from headless_tk import patch_tkinter
    tk, ttk, filedialog, messagebox = patch_tkinter()

_HEADLESS = bool(getattr(tk, "_ytdownloader_headless", False))

class _DummySVTTK:
    def set_theme(self, *_args, **_kwargs):
        pass

    def toggle_theme(self, *_args, **_kwargs):
        pass

try:
    import sv_ttk
except Exception:  # pragma: no cover
    sv_ttk = _DummySVTTK()
else:
    if _HEADLESS:
        sv_ttk = _DummySVTTK()

from downloader import download_video, get_video_info
import threading
from PIL import Image, ImageTk
import requests
from io import BytesIO
import queue
import logging
import yt_dlp
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, List, Any

from config_manager import ConfigManager
from ui_utils import UIConstants, format_file_size, validate_url, validate_proxy, validate_rate_limit, is_ffmpeg_available
from history_manager import HistoryManager
from rss_manager import RSSManager
from localization_manager import LocalizationManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

if logger.hasHandlers():
    logger.handlers.clear()

# File handler
file_handler = logging.FileHandler('ytdownloader.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

class CancelToken:
    """Token for managing download cancellation and pause/resume."""

    def __init__(self, pause_callback=None):
        self.cancelled = False
        self.is_paused = False
        self._pause_callback = pause_callback
        logger.debug("CancelToken initialised: cancelled=%s paused=%s", self.cancelled, self.is_paused)

    def cancel(self):
        """Mark the download as cancelled."""
        self.cancelled = True
        logger.info("CancelToken flagged as cancelled")

    def pause(self):
        """Mark the download as paused."""
        self.is_paused = True
        logger.info("CancelToken flagged as paused")

    def resume(self):
        """Mark the download as resumed."""
        self.is_paused = False
        logger.info("CancelToken flagged as resumed")

    def check(self, d):
        """Check if download should be cancelled or paused."""
        if self._pause_callback:
            external_paused = self._pause_callback()
            if external_paused != self.is_paused:
                self.is_paused = external_paused
        
        if self.cancelled:
            raise yt_dlp.utils.DownloadError("Download cancelled by user.")
        
        pause_check_count = 0
        while self.is_paused:
            pause_check_count += 1
            time.sleep(UIConstants.PAUSE_SLEEP_INTERVAL)
            if self.cancelled:
                raise yt_dlp.utils.DownloadError("Download cancelled by user.")
            if self._pause_callback:
                external_paused = self._pause_callback()
                if not external_paused:
                    self.is_paused = False
                    break

class YTDownloaderGUI:
    """
    The main class for the YTDownloader GUI.
    """
    def __init__(self, master):
        logger.info("Initialising YTDownloaderGUI")
        self.master = master
        self.config = ConfigManager.load_config()

        # Load Language
        lang = self.config.get('language', 'en')
        LocalizationManager.load_language(lang)

        self._setup_main_window()

        # --- Application State ---
        self.dark_mode = tk.BooleanVar(value=self.config.get('dark_mode', True))
        self._video_streams: List[Dict[str, Any]] = []
        self._audio_streams: List[Dict[str, Any]] = []
        self.download_queue: List[Dict[str, Any]] = []
        self.cancel_token: Optional[CancelToken] = None
        self.is_paused = False
        self.ffmpeg_available = is_ffmpeg_available()

        # Initialise History DB
        HistoryManager.init_db()
        self.fetch_thread: Optional[threading.Thread] = None
        self.current_download_item: Optional[Dict[str, Any]] = None
        self.is_fullscreen = False
        self.normal_geometry = None
        self.clipboard_monitor_enabled = tk.BooleanVar(value=True)

        self.ui_queue: queue.Queue = queue.Queue()
        self.master.after(UIConstants.QUEUE_POLL_INTERVAL, self.process_ui_queue)
        self.master.after(1000, self.check_clipboard)
        self.master.after(5000, self.check_scheduled_downloads)

        # --- UI Setup ---
        self._create_widgets()

        # Set initial theme
        theme = "dark" if self.dark_mode.get() else "light"
        logger.debug("Setting initial theme to %s", theme)

    def _setup_main_window(self) -> None:
        """Configure the main window."""
        self.master.title(LocalizationManager.get("app_title"))
        self.master.geometry(f"{UIConstants.WINDOW_MIN_WIDTH}x{UIConstants.WINDOW_MIN_HEIGHT}")
        self.master.minsize(UIConstants.WINDOW_MIN_WIDTH, UIConstants.WINDOW_MIN_HEIGHT)
        self.master.update_idletasks()
        self.normal_geometry = self.master.geometry()

        self.master.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.master.bind('<Escape>', lambda e: self.exit_fullscreen() if self.is_fullscreen else None)
        self.master.bind('<Control-i>', lambda e: self.import_urls_from_file())
        self.master.bind('<Control-I>', lambda e: self.import_urls_from_file())
        self.master.bind('<Control-v>', lambda e: self.paste_url())

        try:
            icon_path = Path(__file__).parent / "icon.ico"
            if icon_path.exists():
                self.master.iconbitmap(str(icon_path))
        except Exception:
            pass

    def _create_widgets(self):
        """Create all UI widgets with a modern layout."""
        self.main_container = ttk.Frame(self.master, padding=20)
        self.main_container.pack(fill="both", expand=True)

        # === HERO SECTION ===
        hero_frame = ttk.Frame(self.main_container)
        hero_frame.pack(fill="x", pady=(0, 20))

        # Title and Theme Toggle
        header_box = ttk.Frame(hero_frame)
        header_box.pack(fill="x", pady=(0, 10))
        
        ttk.Label(header_box, text="YTDownloader", font=("Segoe UI Variable Display", 24, "bold")).pack(side="left")
        
        theme_btn = ttk.Button(header_box, text="🌗", command=self.toggle_theme, width=3)
        theme_btn.pack(side="right")
        self._create_tooltip(theme_btn, LocalizationManager.get("toggle_theme"))

        # URL Input Area
        url_box = ttk.Frame(hero_frame)
        url_box.pack(fill="x")

        self.url_entry = ttk.Entry(url_box, font=("Segoe UI", 11))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=5)
        self.url_entry.bind('<Return>', lambda e: self.fetch_info())
        self._create_tooltip(self.url_entry, LocalizationManager.get("paste_url_tooltip"))

        # Paste Button
        paste_btn = ttk.Button(url_box, text="📋", width=3, command=self.paste_url)
        paste_btn.pack(side="left", padx=(0, 10))
        self._create_tooltip(paste_btn, "Paste from Clipboard")

        self.fetch_button = ttk.Button(url_box, text=LocalizationManager.get("fetch_info"), command=self.fetch_info, style="Accent.TButton", width=15)
        self.fetch_button.pack(side="right")
        self._create_tooltip(self.fetch_button, LocalizationManager.get("fetch_info_tooltip"))

        # Batch Download Button (Visible)
        batch_btn = ttk.Button(url_box, text="Batch", width=6, command=self.import_urls_from_file)
        batch_btn.pack(side="right", padx=(0, 5))
        self._create_tooltip(batch_btn, "Import URLs from text file")


        # === CONTENT AREA (Split View) ===
        content_pane = ttk.PanedWindow(self.main_container, orient="horizontal")
        content_pane.pack(fill="both", expand=True, pady=(0, 20))

        # Left Panel: Preview & Options
        left_panel = ttk.Frame(content_pane)
        content_pane.add(left_panel, weight=1)

        # Preview Card (Initially Hidden)
        self.preview_card = ttk.LabelFrame(left_panel, text=LocalizationManager.get("preview"), padding=15)
        self.preview_card.pack(fill="x", pady=(0, 15))
        
        preview_layout = ttk.Frame(self.preview_card)
        preview_layout.pack(fill="x")
        
        self.thumbnail_label = ttk.Label(preview_layout, background='#333', width=25, anchor="center")
        self.thumbnail_label.pack(side="left", padx=(0, 15))
        
        details_box = ttk.Frame(preview_layout)
        details_box.pack(side="left", fill="both", expand=True)
        
        self.title_label = ttk.Label(details_box, text=LocalizationManager.get("no_video_loaded"), font=("Segoe UI", 12, "bold"), wraplength=300)
        self.title_label.pack(anchor="w", pady=(0, 5))
        
        self.duration_label = ttk.Label(details_box, text=f"{LocalizationManager.get('duration')}: --:--", foreground="gray")
        self.duration_label.pack(anchor="w")

        self.loading_animation_label = ttk.Label(details_box, text=LocalizationManager.get("fetching"), font=("Segoe UI", 10, "italic"))

        # Options Notebook
        self.notebook = ttk.Notebook(left_panel)
        self.notebook.pack(fill="both", expand=True)

        self._create_tabs()

        # Right Panel: Queue & History (Notebook)
        right_panel = ttk.Frame(content_pane)
        content_pane.add(right_panel, weight=1)

        self.right_notebook = ttk.Notebook(right_panel)
        self.right_notebook.pack(fill="both", expand=True, padx=(10, 0))

        # --- Queue Tab ---
        self.queue_tab = ttk.Frame(self.right_notebook)
        self.right_notebook.add(self.queue_tab, text=LocalizationManager.get("queue"))

        queue_header = ttk.Frame(self.queue_tab)
        queue_header.pack(fill="x", pady=(5, 5))

        # Queue Controls
        q_ctrl_box = ttk.Frame(queue_header)
        q_ctrl_box.pack(side="right")

        ttk.Button(q_ctrl_box, text="▲", width=3, command=self.move_queue_up).pack(side="left", padx=2)
        ttk.Button(q_ctrl_box, text="▼", width=3, command=self.move_queue_down).pack(side="left", padx=2)
        ttk.Button(q_ctrl_box, text=LocalizationManager.get("clear_all"), command=self.clear_ui, style="TButton").pack(side="left", padx=(5, 0))

        # Treeview
        tree_frame = ttk.Frame(self.queue_tab)
        tree_frame.pack(fill="both", expand=True)
        
        columns = ("URL", "Status", "Progress")
        self.download_queue_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.download_queue_tree.heading("URL", text=LocalizationManager.get("video"))
        self.download_queue_tree.heading("Status", text=LocalizationManager.get("status"))
        self.download_queue_tree.heading("Progress", text=LocalizationManager.get("progress"))
        
        self.download_queue_tree.column("URL", width=150)
        self.download_queue_tree.column("Status", width=80)
        self.download_queue_tree.column("Progress", width=80)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.download_queue_tree.yview)
        self.download_queue_tree.configure(yscrollcommand=scrollbar.set)

        self.download_queue_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Context Menu
        self.context_menu = tk.Menu(self.master, tearoff=0)
        self.context_menu.add_command(label="Cancel", command=self.cancel_download_item)
        self.context_menu.add_command(label="Remove", command=self.remove_from_queue)
        self.context_menu.add_command(label="Open Folder", command=self.open_file_location)
        self.download_queue_tree.bind("<Button-3>", self.show_context_menu)

        # --- History Tab ---
        self.history_tab = ttk.Frame(self.right_notebook)
        self.right_notebook.add(self.history_tab, text=LocalizationManager.get("history"))

        hist_header = ttk.Frame(self.history_tab)
        hist_header.pack(fill="x", pady=(5, 5))
        ttk.Button(hist_header, text=LocalizationManager.get("refresh"), command=self.load_history).pack(side="left")
        ttk.Button(hist_header, text=LocalizationManager.get("retry_selected"), command=self.retry_history_item).pack(side="left", padx=5)
        ttk.Button(hist_header, text="Play", command=self.play_history_item).pack(side="left", padx=5)
        ttk.Button(hist_header, text=LocalizationManager.get("clear_history"), command=self.clear_history).pack(side="right")

        hist_tree_frame = ttk.Frame(self.history_tab)
        hist_tree_frame.pack(fill="both", expand=True)

        h_cols = ("Title", "Status", "Date")
        self.history_tree = ttk.Treeview(hist_tree_frame, columns=h_cols, show="headings", selectmode="browse")
        self.history_tree.heading("Title", text=LocalizationManager.get("title"))
        self.history_tree.heading("Status", text=LocalizationManager.get("status"))
        self.history_tree.heading("Date", text=LocalizationManager.get("date"))

        self.history_tree.column("Title", width=180)
        self.history_tree.column("Status", width=60)
        self.history_tree.column("Date", width=100)

        h_scroll = ttk.Scrollbar(hist_tree_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=h_scroll.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        h_scroll.pack(side="right", fill="y")

        self.history_tree.bind("<Double-1>", lambda e: self.play_history_item())
        self.load_history() # Initial load

        # === BOTTOM BAR ===
        bottom_bar = ttk.Frame(self.main_container)
        bottom_bar.pack(fill="x", pady=(10, 0))

        # Path Selection
        path_box = ttk.Frame(bottom_bar)
        path_box.pack(fill="x", pady=(0, 10))
        
        ttk.Label(path_box, text=LocalizationManager.get("save_to")).pack(side="left", padx=(0, 5))
        self.path_entry = ttk.Entry(path_box)
        self.path_entry.insert(0, str(Path.home() / "Downloads"))
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ttk.Button(path_box, text="📂", width=3, command=self.browse_path).pack(side="left")

        # Action Buttons
        action_box = ttk.Frame(bottom_bar)
        action_box.pack(fill="x")
        
        self.download_button = ttk.Button(action_box, text=LocalizationManager.get("add_to_queue"), command=self.add_to_queue, style="Accent.TButton", width=20)
        self.download_button.pack(side="right", padx=(5, 0))
        
        self.schedule_button = ttk.Button(action_box, text="🕒 Schedule", command=self.schedule_download_dialog)
        self.schedule_button.pack(side="right", padx=(5, 0))

        self.pause_button = ttk.Button(action_box, text=LocalizationManager.get("pause"), command=self.toggle_pause_resume, state="disabled")
        self.pause_button.pack(side="right", padx=(5, 0))
        
        self.cancel_button = ttk.Button(action_box, text=LocalizationManager.get("cancel"), command=self.cancel_download, state="disabled")
        self.cancel_button.pack(side="right")

        # Status Bar
        self.status_frame = ttk.Frame(self.master, relief="sunken", padding=(5, 2))
        self.status_frame.pack(side="bottom", fill="x")
        
        self.status_label = ttk.Label(self.status_frame, text=LocalizationManager.get("ready"), font=("Segoe UI", 9))
        self.status_label.pack(side="left")
        
        self.progress_bar = ttk.Progressbar(self.status_frame, orient="horizontal", length=200, mode="determinate")
        self.progress_bar.pack(side="right", padx=(0, 5))

    def _create_tabs(self):
        self.video_tab = ttk.Frame(self.notebook, padding=10); self.notebook.add(self.video_tab, text=LocalizationManager.get("tab_video"))
        self.audio_tab = ttk.Frame(self.notebook, padding=10); self.notebook.add(self.audio_tab, text=LocalizationManager.get("tab_audio"))
        self.adv_tab = ttk.Frame(self.notebook, padding=10); self.notebook.add(self.adv_tab, text=LocalizationManager.get("tab_advanced"))
        self.post_tab = ttk.Frame(self.notebook, padding=10); self.notebook.add(self.post_tab, text="Post-Processing")
        self.rss_tab = ttk.Frame(self.notebook, padding=10); self.notebook.add(self.rss_tab, text=LocalizationManager.get("tab_rss"))
        self.settings_tab = ttk.Frame(self.notebook, padding=10); self.notebook.add(self.settings_tab, text=LocalizationManager.get("tab_settings"))

        # Video Tab
        ttk.Label(self.video_tab, text=LocalizationManager.get("quality")).grid(row=0, column=0, sticky="w", pady=5)
        self.video_format_var = tk.StringVar()
        self.video_format_menu = ttk.Combobox(self.video_tab, textvariable=self.video_format_var, state="readonly", width=40)
        self.video_format_menu.grid(row=0, column=1, sticky="ew", padx=10)

        # Audio Tab
        ttk.Label(self.audio_tab, text=LocalizationManager.get("format")).grid(row=0, column=0, sticky="w", pady=5)
        self.audio_format_var = tk.StringVar()
        self.audio_format_menu = ttk.Combobox(self.audio_tab, textvariable=self.audio_format_var, state="readonly", width=40)
        self.audio_format_menu.grid(row=0, column=1, sticky="ew", padx=10)

        self.add_metadata_var = tk.BooleanVar()
        ttk.Checkbutton(self.audio_tab, text=LocalizationManager.get("add_metadata"), variable=self.add_metadata_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=5)

        self.embed_thumbnail_var = tk.BooleanVar()
        ttk.Checkbutton(self.audio_tab, text=LocalizationManager.get("embed_thumbnail"), variable=self.embed_thumbnail_var).grid(row=2, column=0, columnspan=2, sticky="w")

        # Advanced Tab
        self.subtitle_lang_var = tk.StringVar()
        ttk.Label(self.adv_tab, text=LocalizationManager.get("subtitles")).grid(row=0, column=0, sticky="w", pady=5)
        self.subtitle_lang_menu = ttk.Combobox(self.adv_tab, textvariable=self.subtitle_lang_var, state="readonly", width=30)
        self.subtitle_lang_menu.grid(row=0, column=1, sticky="ew", padx=10)

        self.subtitle_format_var = tk.StringVar(value="srt")
        ttk.Combobox(self.adv_tab, textvariable=self.subtitle_format_var, values=["srt", "vtt", "ass"], state="readonly", width=8).grid(row=0, column=2)

        self.playlist_var = tk.BooleanVar()
        ttk.Checkbutton(self.adv_tab, text=LocalizationManager.get("download_playlist"), variable=self.playlist_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
        
        self.chapters_var = tk.BooleanVar()
        ttk.Checkbutton(self.adv_tab, text=LocalizationManager.get("split_chapters"), variable=self.chapters_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

        # Time Range (Download Sections)
        range_frame = ttk.LabelFrame(self.adv_tab, text=LocalizationManager.get("time_range"), padding=5)
        range_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=10)

        ttk.Label(range_frame, text=LocalizationManager.get("start")).pack(side="left")
        self.time_start_entry = ttk.Entry(range_frame, width=8)
        self.time_start_entry.pack(side="left", padx=(2, 10))
        self._create_tooltip(self.time_start_entry, "e.g. 00:01:30")

        ttk.Label(range_frame, text=LocalizationManager.get("end")).pack(side="left")
        self.time_end_entry = ttk.Entry(range_frame, width=8)
        self.time_end_entry.pack(side="left", padx=(2, 0))
        self._create_tooltip(self.time_end_entry, "e.g. 00:02:45")

        # Post-Processing Tab
        ttk.Label(self.post_tab, text="Recode Video to:").grid(row=0, column=0, sticky="w", pady=5)
        self.recode_var = tk.StringVar()
        ttk.Combobox(self.post_tab, textvariable=self.recode_var, values=["", "mp4", "mkv", "avi", "webm"], state="readonly", width=10).grid(row=0, column=1, sticky="w", padx=10)
        ttk.Label(self.post_tab, text="(Leave empty for no recoding)", font=("Segoe UI", 8, "italic")).grid(row=0, column=2, sticky="w")


        # RSS Tab
        ttk.Label(self.rss_tab, text=LocalizationManager.get("rss_channel_url")).pack(fill="x", pady=(0, 5))
        rss_input_frame = ttk.Frame(self.rss_tab)
        rss_input_frame.pack(fill="x", pady=(0, 10))
        self.rss_entry = ttk.Entry(rss_input_frame)
        self.rss_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(rss_input_frame, text=LocalizationManager.get("add"), command=self.add_rss_feed).pack(side="right")

        self.rss_list = tk.Listbox(self.rss_tab, height=6)
        self.rss_list.pack(fill="both", expand=True, pady=(0, 10))

        rss_btn_frame = ttk.Frame(self.rss_tab)
        rss_btn_frame.pack(fill="x")
        ttk.Button(rss_btn_frame, text=LocalizationManager.get("remove"), command=self.remove_rss_feed).pack(side="left")
        ttk.Button(rss_btn_frame, text=LocalizationManager.get("check_now"), command=self.check_rss_feeds).pack(side="right")

        self._load_rss_feeds()

        # Settings Tab
        # FFmpeg Indicator
        ff_status = "✅ Detected" if self.ffmpeg_available else "❌ Not Found"
        ff_color = "green" if self.ffmpeg_available else "red"
        ttk.Label(self.settings_tab, text=LocalizationManager.get("ffmpeg_status")).grid(row=0, column=0, sticky="w", pady=5)
        ff_lbl = ttk.Label(self.settings_tab, text=ff_status, foreground=ff_color)
        ff_lbl.grid(row=0, column=1, sticky="w", padx=10)

        ttk.Button(self.settings_tab, text=LocalizationManager.get("check_updates"), command=self.check_updates).grid(row=0, column=2, padx=10)

        ttk.Label(self.settings_tab, text=LocalizationManager.get("proxy")).grid(row=1, column=0, sticky="w", pady=5)
        self.proxy_entry = ttk.Entry(self.settings_tab, width=30)
        self.proxy_entry.grid(row=1, column=1, padx=10)
        if self.config.get('proxy'): self.proxy_entry.insert(0, self.config.get('proxy', ''))

        ttk.Label(self.settings_tab, text=LocalizationManager.get("rate_limit")).grid(row=2, column=0, sticky="w", pady=5)
        self.ratelimit_entry = ttk.Entry(self.settings_tab, width=30)
        self.ratelimit_entry.grid(row=2, column=1, padx=10)
        if self.config.get('rate_limit'): self.ratelimit_entry.insert(0, self.config.get('rate_limit', ''))

        # Cookies
        ttk.Label(self.settings_tab, text=LocalizationManager.get("browser_cookies")).grid(row=3, column=0, sticky="w", pady=5)
        self.cookies_browser_var = tk.StringVar()
        self.cookies_browser_menu = ttk.Combobox(self.settings_tab, textvariable=self.cookies_browser_var, values=["", "chrome", "firefox", "edge"], state="readonly", width=20)
        self.cookies_browser_menu.grid(row=3, column=1, padx=10)

        ttk.Label(self.settings_tab, text=LocalizationManager.get("profile")).grid(row=4, column=0, sticky="w", pady=5)
        self.cookies_profile_entry = ttk.Entry(self.settings_tab, width=30)
        self.cookies_profile_entry.grid(row=4, column=1, padx=10)

        # Language Selection
        ttk.Label(self.settings_tab, text=LocalizationManager.get("language")).grid(row=5, column=0, sticky="w", pady=5)
        self.lang_var = tk.StringVar(value=LocalizationManager._current_lang)
        self.lang_menu = ttk.Combobox(self.settings_tab, textvariable=self.lang_var, values=LocalizationManager.get_available_languages(), state="readonly", width=10)
        self.lang_menu.grid(row=5, column=1, padx=10)
        self.lang_menu.bind("<<ComboboxSelected>>", self.change_language)

    def check_updates(self):
        import webbrowser
        if messagebox.askyesno(LocalizationManager.get("updates_title"), LocalizationManager.get("updates_msg")):
            webbrowser.open("https://github.com/yourusername/YTDownloader/releases")

    def change_language(self, event=None):
        lang = self.lang_var.get()
        if lang != LocalizationManager._current_lang:
            self.config['language'] = lang
            ConfigManager.save_config(self.config)
            self.show_toast("Please restart to apply language changes")

    def load_history(self):
        """Load history from DB into the treeview."""
        for i in self.history_tree.get_children():
            self.history_tree.delete(i)

        self._history_data = HistoryManager.get_history(limit=100)
        for i, item in enumerate(self._history_data):
            self.history_tree.insert("", "end", iid=i, values=(item['title'], item['status'], item['timestamp']))

    def retry_history_item(self):
        sel = self.history_tree.selection()
        if not sel:
            self.show_toast(LocalizationManager.get("select_item"))
            return

        idx = int(sel[0])
        if idx < 0 or idx >= len(self._history_data): return

        item = self._history_data[idx]
        url = item.get('url')
        if not url: return

        # Re-populate fields
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, url)
        self.fetch_info()
        self.show_toast("Loaded into main view")
        self.notebook.select(self.video_tab) # Switch to video tab

    def play_history_item(self):
        sel = self.history_tree.selection()
        if not sel: return

        idx = int(sel[0])
        if idx < 0 or idx >= len(self._history_data): return

        item = self._history_data[idx]
        path = item.get('file_path')

        if path and os.path.exists(path):
            self._open_file(path)
        else:
             # Fallback to opening the folder
             out_path = item.get('output_path')
             if out_path and os.path.exists(out_path):
                 self._open_file(out_path)
             else:
                 self.show_toast("File not found")

    def _open_file(self, path):
        try:
            if sys.platform == 'win32': os.startfile(path)
            elif sys.platform == 'darwin': subprocess.Popen(['open', path])
            else: subprocess.Popen(['xdg-open', path])
        except Exception as e:
            logger.error(f"Failed to open file {path}: {e}")
            self.show_toast("Error opening file")

    def clear_history(self):
        if messagebox.askyesno(LocalizationManager.get("confirm_title"), LocalizationManager.get("clear_history_msg")):
            HistoryManager.clear_history()
            self.load_history()

    def move_queue_up(self):
        sel = self.download_queue_tree.selection()
        if not sel: return
        idx = int(sel[0])
        if idx > 0:
            self.download_queue[idx], self.download_queue[idx-1] = self.download_queue[idx-1], self.download_queue[idx]
            self.update_download_queue_list()
            self.download_queue_tree.selection_set(str(idx-1))

    def move_queue_down(self):
        sel = self.download_queue_tree.selection()
        if not sel: return
        idx = int(sel[0])
        if idx < len(self.download_queue) - 1:
            self.download_queue[idx], self.download_queue[idx+1] = self.download_queue[idx+1], self.download_queue[idx]
            self.update_download_queue_list()
            self.download_queue_tree.selection_set(str(idx+1))

    def _create_tooltip(self, widget, text):
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(tooltip, text=text, background="#333", foreground="white", relief="solid", borderwidth=0, padding=5)
            label.pack()
            widget.tooltip = tooltip
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)

    def _load_rss_feeds(self):
        self.rss_list.delete(0, tk.END)
        feeds = self.config.get('rss_feeds', [])
        for feed in feeds:
            self.rss_list.insert(tk.END, feed)

    def add_rss_feed(self):
        url = self.rss_entry.get().strip()
        if not url: return

        feeds = self.config.get('rss_feeds', [])
        if url not in feeds:
            feeds.append(url)
            self.config['rss_feeds'] = feeds
            ConfigManager.save_config(self.config)
            self._load_rss_feeds()
            self.rss_entry.delete(0, tk.END)

    def remove_rss_feed(self):
        sel = self.rss_list.curselection()
        if not sel: return

        feed = self.rss_list.get(sel[0])
        feeds = self.config.get('rss_feeds', [])
        if feed in feeds:
            feeds.remove(feed)
            self.config['rss_feeds'] = feeds
            ConfigManager.save_config(self.config)
            self._load_rss_feeds()

    def check_rss_feeds(self):
        feeds = self.config.get('rss_feeds', [])
        if not feeds:
            self.show_toast("No RSS feeds configured")
            return

        self.status_label.config(text="Checking RSS feeds...")

        def _check():
            found_count = 0
            for feed_url in feeds:
                video = RSSManager.get_latest_video(feed_url)
                if video:
                    # Check if already downloaded (optional, for now just check if in queue or history)
                    # For simplicity, we'll just show what we found and offer to add.
                    # Or better, auto-add to queue if 'Smart Download' was fully implemented.
                    # Here we will just fetch info for the latest one found to demo.
                    self.ui_queue.put((lambda: self.url_entry.delete(0, tk.END), {}))
                    self.ui_queue.put((lambda: self.url_entry.insert(0, video['link']), {}))
                    self.ui_queue.put((self.fetch_info, {}))
                    found_count += 1
                    break # Just load the first one found for now

            if found_count == 0:
                 self.ui_queue.put((self.show_toast, {'message': LocalizationManager.get("no_new_videos")}))
            else:
                 self.ui_queue.put((self.show_toast, {'message': LocalizationManager.get("loaded_rss")}))

        threading.Thread(target=_check, daemon=True).start()

    def check_clipboard(self):
        """Monitor clipboard for YouTube links."""
        if self.clipboard_monitor_enabled.get():
            try:
                content = self.master.clipboard_get()
                if validate_url(content) and "youtube.com" in content and content != self.url_entry.get():
                    # Optional: Auto-paste or just notify?
                    # For now, let's just log it. Auto-paste can be annoying.
                    pass
            except:
                pass
        self.master.after(2000, self.check_clipboard)

    def paste_url(self):
        try:
            content = self.master.clipboard_get()
            if validate_url(content):
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, content)
                self.fetch_info()
        except:
            pass

    def show_toast(self, message, duration=2000):
        """Show a non-intrusive toast notification."""
        toast = tk.Toplevel(self.master)
        toast.wm_overrideredirect(True)
        x = self.master.winfo_x() + self.master.winfo_width() // 2 - 100
        y = self.master.winfo_y() + self.master.winfo_height() - 60
        toast.wm_geometry(f"200x40+{x}+{y}")

        label = ttk.Label(toast, text=message, anchor="center", background="#4caf50", foreground="white", font=("Segoe UI", 10))
        label.pack(fill="both", expand=True)

        toast.after(duration, toast.destroy)

    # --- Original Logic Methods (Preserved) ---

    def toggle_theme(self) -> None:
        sv_ttk.toggle_theme()
        self.dark_mode.set(not self.dark_mode.get())
        self.config['dark_mode'] = self.dark_mode.get()
        ConfigManager.save_config(self.config)

    def process_ui_queue(self):
        try:
            while True:
                task, kwargs = self.ui_queue.get_nowait()
                task(**kwargs)
        except queue.Empty:
            pass
        self.master.after(UIConstants.QUEUE_POLL_INTERVAL, self.process_ui_queue)

    def _safe_clear_ui(self):
        if self.is_downloading() or self.cancel_token:
            return
        self.clear_ui()
    
    def clear_ui(self):
        if self.is_downloading(): return
        self.url_entry.delete(0, tk.END)
        self.title_label.config(text="No video loaded")
        self.duration_label.config(text="Duration: --:--")
        self.thumbnail_label.config(image=None)
        self.thumbnail_label.image = None
        self.video_format_menu.set(''); self.video_format_menu.config(values=[])
        self.audio_format_menu.set(''); self.audio_format_menu.config(values=[])
        self._video_streams = []
        self._audio_streams = []
        self.subtitle_lang_menu.set(''); self.subtitle_lang_menu.config(values=[])
        self.status_label.config(text="Ready")
        self.progress_bar['value'] = 0

    def fetch_info(self):
        url = self.url_entry.get().strip()
        if not url:
            self.show_toast("Please enter a URL")
            return
        if not validate_url(url):
            self.show_toast("Invalid URL")
            return

        self.loading_animation_label.pack(pady=5)
        self.fetch_button.config(state="disabled")
        self.status_label.config(text="Fetching video information...")

        def _fetch():
            try:
                cookies_browser = self.cookies_browser_var.get()
                cookies_profile = self.cookies_profile_entry.get().strip()
                info = get_video_info(url, cookies_from_browser=cookies_browser, cookies_from_browser_profile=cookies_profile)

                if not info: raise yt_dlp.utils.DownloadError("Failed to fetch video information.")

                self.ui_queue.put((self.title_label.config, {'text': info.get('title', 'N/A')}))
                self.ui_queue.put((self.duration_label.config, {'text': f"Duration: {info.get('duration', 'N/A')}"}))
                self.ui_queue.put((self.status_label.config, {'text': "Video info loaded."}))

                self._video_streams = info.get('video_streams', [])
                self._audio_streams = info.get('audio_streams', [])

                # Subtitles
                subtitles = info.get('subtitles', {})
                if subtitles:
                    self.ui_queue.put((self.subtitle_lang_menu.config, {'values': list(subtitles.keys())}))
                else:
                    self.ui_queue.put((self.subtitle_lang_menu.config, {'values': ['No subtitles available']}))
                    self.ui_queue.put((self.subtitle_lang_menu.set, {'value': 'No subtitles available'}))

                # Formats
                video_formats = [f"{s.get('resolution', 'N/A')}@{s.get('fps', 'N/A')}fps ({s.get('ext', 'N/A').upper()}) - {s.get('format_id', 'N/A')}" for s in self._video_streams]
                self.ui_queue.put((self.video_format_menu.config, {'values': video_formats}))
                if video_formats: self.ui_queue.put((self.video_format_menu.set, {'value': video_formats[0]}))

                audio_formats = [f"{s.get('abr', 'N/A')}kbps ({s.get('ext', 'N/A').upper()}) - {s.get('format_id', 'N/A')}" for s in self._audio_streams]
                self.ui_queue.put((self.audio_format_menu.config, {'values': audio_formats}))
                if audio_formats: self.ui_queue.put((self.audio_format_menu.set, {'value': audio_formats[0]}))

                # Thumbnail
                if info.get('thumbnail'):
                    try:
                        response = requests.get(info['thumbnail'], timeout=5)
                        response.raise_for_status()
                        img = Image.open(BytesIO(response.content))
                        img.thumbnail(UIConstants.THUMBNAIL_SIZE)
                        photo = ImageTk.PhotoImage(img)
                        self.ui_queue.put((self.thumbnail_label.config, {'image': photo}))
                        self.thumbnail_label.image = photo
                    except Exception: pass

            except Exception as e:
                self.handle_error_threadsafe("Fetch Failed", e)
            finally:
                self.ui_queue.put((self.loading_animation_label.pack_forget, {}))
                self.ui_queue.put((self.fetch_button.config, {'state': "normal"}))

        self.fetch_thread = threading.Thread(target=_fetch, daemon=True)
        self.fetch_thread.start()

    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            self.update_disk_usage()

    def update_disk_usage(self):
        path = self.path_entry.get()
        if not os.path.exists(path): return
        try:
            import shutil
            total, used, free = shutil.disk_usage(path)
            self.status_label.config(text=f"Free Space: {format_file_size(free)}")
        except Exception:
            pass

    def schedule_download_dialog(self):
        """Open a dialog to schedule the download."""
        if not self.url_entry.get().strip():
            self.show_toast("Enter URL first")
            return

        time_str = simpledialog.askstring("Schedule Download", "Enter start time (HH:MM 24h format):", parent=self.master)
        if not time_str: return

        try:
            # Validate time format
            scheduled_time = datetime.datetime.strptime(time_str, "%H:%M").time()
            now = datetime.datetime.now()
            scheduled_datetime = datetime.datetime.combine(now.date(), scheduled_time)
            if scheduled_datetime < now:
                scheduled_datetime += datetime.timedelta(days=1) # Next day

            self.add_to_queue(scheduled_time=scheduled_datetime)
            self.show_toast(f"Scheduled for {time_str}")

        except ValueError:
            messagebox.showerror("Invalid Time", "Please enter time in HH:MM format")

    def check_scheduled_downloads(self):
        """Check queue for scheduled items."""
        now = datetime.datetime.now()
        for item in self.download_queue:
            if item['status'].startswith("Scheduled"):
                sched_time = item.get('scheduled_time')
                if sched_time and now >= sched_time:
                    item['status'] = 'Queued' # Ready to start
                    if not self.is_downloading():
                        self.process_download_queue()
        self.update_download_queue_list()
        self.master.after(5000, self.check_scheduled_downloads)

    def add_to_queue(self, scheduled_time=None):
        url = self.url_entry.get().strip()
        if not url or not validate_url(url):
            self.show_toast("Invalid URL")
            return

        video_format = self.video_format_var.get()
        if not video_format:
            self.show_toast("Select a video format")
            return

        proxy = self.proxy_entry.get().strip()
        if proxy and not validate_proxy(proxy):
            messagebox.showerror(LocalizationManager.get("invalid_proxy"), LocalizationManager.get("invalid_proxy"))
            return

        rate_limit = self.ratelimit_entry.get().strip()
        if rate_limit and not validate_rate_limit(rate_limit):
            messagebox.showerror(LocalizationManager.get("invalid_rate_limit"), LocalizationManager.get("invalid_rate_limit"))
            return
        
        output_path = self.path_entry.get().strip()
        if not Path(output_path).exists():
            messagebox.showerror(LocalizationManager.get("invalid_path"), LocalizationManager.get("invalid_path"))
            return

        self.config.update({'proxy': proxy, 'rate_limit': rate_limit})
        ConfigManager.save_config(self.config)

        # Parse time range
        start = self.time_start_entry.get().strip()
        end = self.time_end_entry.get().strip()
        download_sections = f"*{start}-{end}" if start and end else None

        status = "Queued"
        if scheduled_time:
            status = f"Scheduled ({scheduled_time.strftime('%H:%M')})"

        download_item = {
            "url": url,
            "video_format": video_format,
            "audio_format": self.audio_format_var.get(),
            "subtitle_lang": self.subtitle_lang_var.get() if self.subtitle_lang_var.get() != 'No subtitles available' else None,
            "subtitle_format": self.subtitle_format_var.get(),
            "output_path": output_path,
            "playlist": self.playlist_var.get(),
            "split_chapters": self.chapters_var.get(),
            "proxy": proxy or None,
            "rate_limit": rate_limit or None,
            "cookies_browser": self.cookies_browser_var.get() or None,
            "cookies_profile": self.cookies_profile_entry.get().strip() or None,
            "download_sections": download_sections,
            "add_metadata": self.add_metadata_var.get(),
            "embed_thumbnail": self.embed_thumbnail_var.get(),
            "recode_video": self.recode_var.get() if self.recode_var.get() else None,
            "scheduled_time": scheduled_time,
            "status": status, "size": "N/A", "speed": "N/A", "eta": "N/A"
        }
        self.download_queue.append(download_item)
        self.update_download_queue_list()
        if not scheduled_time:
            self.show_toast("Added to Queue")
            if not self.is_downloading():
                self.process_download_queue()

    def update_download_queue_list(self):
        for i in self.download_queue_tree.get_children():
            self.download_queue_tree.delete(i)
        for i, item in enumerate(self.download_queue):
            self.download_queue_tree.insert("", "end", iid=i, values=(item['url'], item['status'], f"{item.get('size', 'N/A')} | {item.get('speed', 'N/A')}"))

    def is_downloading(self):
        return any(item['status'] == 'Downloading' for item in self.download_queue)

    def process_download_queue(self):
        if not self.is_downloading():
            for item in self.download_queue:
                if item['status'] == 'Queued':
                    self.start_download_thread(item)
                    break

    def start_download_thread(self, item):
        item['status'] = 'Downloading'
        self.current_download_item = item
        self.is_paused = False
        self.update_download_queue_list()
        self.download_button.config(state="disabled")
        self.pause_button.config(state="normal", text=LocalizationManager.get("pause"))
        self.cancel_button.config(state="normal")

        thread = threading.Thread(target=self.download, args=(item,))
        thread.daemon = True
        thread.start()

    def download(self, item):
        self.cancel_token = CancelToken(pause_callback=lambda: self.is_paused)
        try:
            if self.is_paused: self.cancel_token.pause()

            # Extract Format IDs
            video_fmt_str = item.get('video_format', 'best')
            video_format = 'best' # Default
            if video_fmt_str == 'best':
                video_format = 'best'
            else:
                video_id = self._extract_format_id(video_fmt_str)
                audio_id = self._extract_format_id(item.get('audio_format', ''))
                # Logic to combine if needed...
                video_stream = next((s for s in self._video_streams if s.get('format_id') == video_id), None)
                if video_stream and video_stream.get('acodec') != 'none':
                    video_format = video_id
                else:
                    if not audio_id: raise ValueError("Audio format missing for video-only stream.")
                    video_format = f"{video_id}+{audio_id}"

            download_video(
                item['url'], self.progress_hook, item,
                item['playlist'], video_format, item['output_path'],
                item['subtitle_lang'], item['subtitle_format'], item['split_chapters'],
                item['proxy'], item['rate_limit'], self.cancel_token,
                item.get('cookies_browser'), item.get('cookies_profile'),
                item.get('download_sections'), item.get('add_metadata'), item.get('embed_thumbnail'),
                item.get('recode_video')
            )
            item['status'] = 'Completed'
            self.ui_queue.put((self._safe_clear_ui, {}))
            self.ui_queue.put((self.show_toast, {'message': LocalizationManager.get("download_complete")}))

            # Save to History
            final_path = item.get('final_filename', item['output_path'])

            HistoryManager.add_entry(
                item['url'],
                item.get('title', 'Unknown'),
                item['output_path'],
                video_format,
                "Completed",
                item.get('size', 'N/A'),
                file_path=final_path
            )
            self.ui_queue.put((self.load_history, {}))

        except yt_dlp.utils.DownloadError as e:
            if "cancelled by user" in str(e):
                item['status'] = 'Cancelled'
            else:
                item['status'] = 'Error'
                self.handle_error_threadsafe(LocalizationManager.get("download_error"), e)

            HistoryManager.add_entry(item['url'], "Failed Download", item['output_path'], video_format, "Error", "0")
            self.ui_queue.put((self.load_history, {}))

        except Exception as e:
            item['status'] = 'Error'
            self.handle_error_threadsafe(LocalizationManager.get("unexpected_error"), e)

            HistoryManager.add_entry(item['url'], "Failed Download", item['output_path'], video_format, "Error", "0")
            self.ui_queue.put((self.load_history, {}))
        finally:
            self.cancel_token = None
            self.current_download_item = None
            self.is_paused = False
            self.ui_queue.put((self.download_button.config, {'state': "normal"}))
            self.ui_queue.put((self.pause_button.config, {'state': "disabled", 'text': LocalizationManager.get("pause")}))
            self.ui_queue.put((self.cancel_button.config, {'state': "disabled"}))
            self.ui_queue.put((self.update_download_queue_list, {}))
            if item['status'] != 'Cancelled':
                self.ui_queue.put((self.process_download_queue, {}))

    def _extract_format_id(self, fmt_str):
        if not fmt_str: return None
        parts = fmt_str.rsplit(' - ', 1)
        return parts[-1].strip() if parts else fmt_str

    def progress_hook(self, d, item):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                pct = (downloaded / total) * 100
                self.ui_queue.put((self.progress_bar.config, {'value': pct}))

            item['size'] = format_file_size(total)
            item['speed'] = format_file_size(d.get('speed', 0)) + "/s"
            item['eta'] = f"{int(d.get('eta', 0))}s"

            # Update title if available from d
            if 'filename' in d:
                item['title'] = Path(d['filename']).stem
                item['final_filename'] = d['filename']

            self.ui_queue.put((self.status_label.config, {'text': f"Downloading... {int(pct)}%"}))
            self.ui_queue.put((self.update_download_queue_list, {}))

        elif d['status'] == 'finished':
            if 'filename' in d:
                item['final_filename'] = d['filename']
            self.ui_queue.put((self.progress_bar.config, {'value': 100}))
            self.ui_queue.put((self.status_label.config, {'text': "Processing..."}))

    def handle_error_threadsafe(self, title, error):
        """Queue error message to be shown on main thread."""
        def show():
            messagebox.showerror(title, str(error))
        self.ui_queue.put((show, {}))

    def import_urls_from_file(self, event=None):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not file_path: return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            valid_urls = [u for u in urls if validate_url(u)]
            if not valid_urls:
                self.show_toast("No Valid URLs found")
                return

            output_path = self.path_entry.get().strip()
            proxy = self.proxy_entry.get().strip()

            for url in valid_urls:
                self.download_queue.append({
                    "url": url, "video_format": "best", "audio_format": "best",
                    "subtitle_lang": None, "subtitle_format": "srt",
                    "output_path": output_path, "playlist": False, "split_chapters": False,
                    "proxy": proxy or None, "rate_limit": None,
                    "status": "Queued", "size": "N/A"
                })

            self.update_download_queue_list()
            self.show_toast(f"Imported {len(valid_urls)} URLs")
            if not self.is_downloading(): self.process_download_queue()

        except Exception as e:
            messagebox.showerror(LocalizationManager.get("import_error"), str(e))

    def cancel_download(self):
        if self.cancel_token:
            if messagebox.askyesno(LocalizationManager.get("confirm_title"), LocalizationManager.get("cancel_download_msg")):
                self.cancel_token.cancel()

    def toggle_pause_resume(self):
        if not self.cancel_token: return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.cancel_token.pause()
            self.pause_button.config(text=LocalizationManager.get("resume"))
            self.status_label.config(text="Paused")
        else:
            self.cancel_token.resume()
            self.pause_button.config(text=LocalizationManager.get("pause"))
            self.status_label.config(text="Resuming...")

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.master.attributes('-fullscreen', self.is_fullscreen)
        if not self.is_fullscreen and self.normal_geometry:
            self.master.geometry(self.normal_geometry)

    def exit_fullscreen(self):
        if self.is_fullscreen: self.toggle_fullscreen()

    def show_about(self):
        messagebox.showinfo("About", "YTDownloader v3.0\n\nAdvanced YouTube Video Downloader")

    def show_context_menu(self, event):
        if self.download_queue_tree.identify_row(event.y):
            self.download_queue_tree.selection_set(self.download_queue_tree.identify_row(event.y))
            self.context_menu.post(event.x_root, event.y_root)

    def remove_from_queue(self):
        sel = self.download_queue_tree.selection()
        if not sel:
            self.show_toast("Select an item")
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.download_queue):
            self.download_queue.pop(idx)
            self.update_download_queue_list()

    def cancel_download_item(self):
        sel = self.download_queue_tree.selection()
        if not sel:
            self.show_toast("Select an item")
            return
        idx = int(sel[0])
        if self.download_queue[idx]['status'] == 'Downloading':
            self.cancel_download()
        else:
            self.download_queue[idx]['status'] = 'Cancelled'
            self.update_download_queue_list()

    def open_file_location(self):
        sel = self.download_queue_tree.selection()
        if not sel:
            self.show_toast("Select an item")
            return
        idx = int(sel[0])
        path = self.download_queue[idx]['output_path']
        if sys.platform == 'win32': os.startfile(path)
        elif sys.platform == 'darwin': subprocess.Popen(['open', path])
        else: subprocess.Popen(['xdg-open', path])

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = YTDownloaderGUI(root)
        if not _HEADLESS:
            sv_ttk.set_theme("dark" if app.dark_mode.get() else "light")
        root.mainloop()
    except Exception as e:
        logger.exception("Fatal error")
