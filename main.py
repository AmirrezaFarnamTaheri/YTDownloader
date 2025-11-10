import tkinter as tk

# Try to initialise Tk to determine if a display is available. If not, fall back to
# a lightweight headless implementation so that tests can exercise the GUI logic
# without an X server.
try:  # pragma: no cover - exercised implicitly in tests
    _test_root = tk.Tk()
    _test_root.destroy()
    tk._ytdownloader_headless = False  # type: ignore[attr-defined]
    from tkinter import ttk, filedialog, messagebox  # type: ignore
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
except Exception:  # pragma: no cover - fallback when ttk themes are unavailable
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
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Any

class CancelToken:
    """Token for managing download cancellation and pause/resume."""

    def __init__(self, pause_callback=None):
        self.cancelled = False
        self.is_paused = False
        self._pause_callback = pause_callback  # Callback to check external pause state
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
        logger.debug("CancelToken check invoked with status=%s", d.get('status') if isinstance(d, dict) else None)
        
        # Check external pause state if callback provided
        if self._pause_callback:
            external_paused = self._pause_callback()
            if external_paused != self.is_paused:
                self.is_paused = external_paused
                logger.debug("Pause state synced from external: %s", self.is_paused)
        
        if self.cancelled:
            logger.warning("Cancellation detected during check")
            raise yt_dlp.utils.DownloadError("Download cancelled by user.")
        
        # Handle pause state with proper checking
        pause_check_count = 0
        while self.is_paused:
            pause_check_count += 1
            if pause_check_count % 10 == 0:  # Log every 5 seconds (10 * 0.5s)
                logger.debug("Download still paused (check #%d)", pause_check_count)
            time.sleep(UIConstants.PAUSE_SLEEP_INTERVAL)
            if self.cancelled:
                logger.warning("Cancellation detected while paused")
                raise yt_dlp.utils.DownloadError("Download cancelled by user.")
            # Re-check external pause state periodically
            if self._pause_callback:
                external_paused = self._pause_callback()
                if not external_paused:
                    self.is_paused = False
                    logger.info("Resume detected from external state")
                    break
        logger.debug("CancelToken check completed without cancellation")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

if logger.hasHandlers():
    logger.handlers.clear()

# File handler for detailed debug logs
file_handler = logging.FileHandler('ytdownloader.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler for INFO level logs
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_FILE = Path.home() / '.ytdownloader' / 'config.json'
CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Constants
class UIConstants:
    """Class to hold UI-related constants."""
    THUMBNAIL_SIZE = (160, 120)  # Larger thumbnail for better visibility
    WINDOW_MIN_WIDTH = 1000
    WINDOW_MIN_HEIGHT = 750
    QUEUE_POLL_INTERVAL = 100  # milliseconds
    PAUSE_SLEEP_INTERVAL = 0.5  # seconds
    DEFAULT_PADDING = 10
    BUTTON_PADDING = 8
    ENTRY_PADDING = 5

def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    logger.debug("Attempting to load configuration from %s", CONFIG_FILE)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("Configuration loaded successfully: keys=%s", list(data.keys()))
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load config: {e}")
    return {}

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    logger.debug("Persisting configuration to %s with keys=%s", CONFIG_FILE, list(config.keys()))
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved successfully")
    except IOError as e:
        logger.error(f"Failed to save config: {e}")

def validate_url(url: str) -> bool:
    """Validate if URL is a valid video URL."""
    url = url.strip()
    valid = url.startswith(('http://', 'https://')) and len(url) > 10
    logger.debug("validate_url('%s') -> %s", url, valid)
    return valid

def validate_proxy(proxy: str) -> bool:
    """Validate proxy format."""
    if not proxy.strip():
        return True  # Empty is valid (no proxy)
    # Basic proxy validation: should contain :// and have a host:port
    valid = '://' in proxy and ':' in proxy.split('://', 1)[1]
    logger.debug("validate_proxy('%s') -> %s", proxy, valid)
    return valid

def validate_rate_limit(rate_limit: str) -> bool:
    """Validate rate limit format (e.g., 50K, 4.2M)."""
    if not rate_limit.strip():
        return True  # Empty is valid (no limit)
    import re
    valid = bool(re.match(r'^\d+(\.\d+)?[KMGT]?$', rate_limit.strip()))
    logger.debug("validate_rate_limit('%s') -> %s", rate_limit, valid)
    return valid

def format_file_size(size_bytes: Optional[float]) -> str:
    """Format file size for display."""
    if size_bytes is None or size_bytes == 'N/A':
        return 'N/A'
    try:
        size_bytes = float(size_bytes)
        if size_bytes == 0:
            return "0.00 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                formatted = f"{size_bytes:.2f} {unit}"
                logger.debug("format_file_size -> %s", formatted)
                return formatted
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"  # Should be unreachable with normal file sizes
    except (ValueError, TypeError):
        return 'N/A'

class YTDownloaderGUI:
    """
    The main class for the YTDownloader GUI, responsible for creating and managing the UI.
    """
    def __init__(self, master):
        """
        Initializes the main GUI window and its components.
        :param master: The root Tkinter window.
        """
        logger.info("Initialising YTDownloaderGUI")
        self.master = master
        self._setup_main_window()

        # Load configuration
        self.config = load_config()

        # --- Application State ---
        self.dark_mode = tk.BooleanVar(value=self.config.get('dark_mode', True))
        self._video_streams: List[Dict[str, Any]] = []
        self._audio_streams: List[Dict[str, Any]] = []
        self.download_queue: List[Dict[str, Any]] = []
        self.cancel_token: Optional[CancelToken] = None
        self.is_paused = False
        self.fetch_thread: Optional[threading.Thread] = None
        self.current_download_item: Optional[Dict[str, Any]] = None
        self.is_fullscreen = False
        self.normal_geometry = None  # Store normal window geometry

        self.ui_queue: queue.Queue = queue.Queue()
        self.master.after(UIConstants.QUEUE_POLL_INTERVAL, self.process_ui_queue)
        logger.debug("UI queue polling scheduled every %sms", UIConstants.QUEUE_POLL_INTERVAL)

        # --- UI Setup ---
        # Main frame with improved padding
        self.frame = ttk.Frame(master, padding=f"{UIConstants.DEFAULT_PADDING}")
        self.frame.grid(row=0, column=0, sticky="nsew", padx=UIConstants.DEFAULT_PADDING, pady=UIConstants.DEFAULT_PADDING)
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)

        # Top frame for URL entry and theme switcher with improved layout
        self.top_frame = ttk.LabelFrame(self.frame, text="Video URL", padding=UIConstants.DEFAULT_PADDING)
        self.top_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, UIConstants.DEFAULT_PADDING))
        self.top_frame.grid_columnconfigure(1, weight=1)

        self.url_label = ttk.Label(self.top_frame, text="URL:", font=('', 9, 'bold'))
        self.url_label.grid(row=0, column=0, padx=(0, UIConstants.ENTRY_PADDING), sticky="w")
        
        self.url_entry = ttk.Entry(self.top_frame, width=60, font=('', 9))
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=UIConstants.ENTRY_PADDING)
        self.url_entry.bind('<Return>', lambda e: self.fetch_info())  # Enter key support
        
        # Add tooltip for URL entry
        self._create_tooltip(self.url_entry, "Enter a YouTube URL or any supported video URL")
        
        self.fetch_button = ttk.Button(
            self.top_frame, 
            text="🔍 Fetch Info", 
            command=self.fetch_info,
            width=15
        )
        self.fetch_button.grid(row=0, column=2, padx=UIConstants.ENTRY_PADDING)
        self._create_tooltip(self.fetch_button, "Fetch video information and available formats")
        
        self.theme_button = ttk.Button(
            self.top_frame, 
            text="🎨 Theme", 
            command=self.toggle_theme,
            width=12
        )
        self.theme_button.grid(row=0, column=3, padx=UIConstants.ENTRY_PADDING)
        self._create_tooltip(self.theme_button, "Toggle between light and dark theme")

        # Menu
        self.menubar = tk.Menu(master)
        
        # File menu
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="Import URLs from File...", command=self.import_urls_from_file, accelerator="Ctrl+I")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.master.quit)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        
        # Help menu
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.help_menu.add_command(label="About", command=self.show_about)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)
        master.config(menu=self.menubar)
        
        # Bind keyboard shortcut
        master.bind('<Control-i>', lambda e: self.import_urls_from_file())
        master.bind('<Control-I>', lambda e: self.import_urls_from_file())

        # Video Info Frame with improved layout
        self.info_frame = ttk.LabelFrame(self.frame, text="📹 Video Information", padding=UIConstants.DEFAULT_PADDING)
        self.info_frame.grid(row=1, column=0, columnspan=4, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self.info_frame.grid_columnconfigure(1, weight=1)
        
        self.thumbnail_label = ttk.Label(self.info_frame, background='#f0f0f0', relief='sunken', borderwidth=2)
        self.thumbnail_label.grid(row=0, column=0, rowspan=3, padx=(0, UIConstants.DEFAULT_PADDING), sticky="nw")
        
        # Title with better formatting
        title_frame = ttk.Frame(self.info_frame)
        title_frame.grid(row=0, column=1, sticky="ew", pady=(0, UIConstants.ENTRY_PADDING))
        ttk.Label(title_frame, text="Title:", font=('', 9, 'bold')).grid(row=0, column=0, sticky="w")
        self.title_label = ttk.Label(title_frame, text="N/A", font=('', 9), foreground='#666')
        self.title_label.grid(row=0, column=1, sticky="w", padx=(UIConstants.ENTRY_PADDING, 0))
        
        # Duration with better formatting
        duration_frame = ttk.Frame(self.info_frame)
        duration_frame.grid(row=1, column=1, sticky="ew", pady=(0, UIConstants.ENTRY_PADDING))
        ttk.Label(duration_frame, text="Duration:", font=('', 9, 'bold')).grid(row=0, column=0, sticky="w")
        self.duration_label = ttk.Label(duration_frame, text="N/A", font=('', 9), foreground='#666')
        self.duration_label.grid(row=0, column=1, sticky="w", padx=(UIConstants.ENTRY_PADDING, 0))

        # Tabs for options with improved styling
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.grid(row=2, column=0, columnspan=4, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="nsew")
        self.frame.grid_rowconfigure(2, weight=1)  # Allow notebook to expand

        self.video_tab = ttk.Frame(self.notebook)
        self.audio_tab = ttk.Frame(self.notebook)
        self.subtitle_tab = ttk.Frame(self.notebook)
        self.playlist_tab = ttk.Frame(self.notebook)
        self.chapters_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.cookies_tab = ttk.Frame(self.notebook)
        self.downloads_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.video_tab, text="🎬 Video")
        self.notebook.add(self.audio_tab, text="🎵 Audio")
        self.notebook.add(self.subtitle_tab, text="📝 Subtitles")
        self.notebook.add(self.playlist_tab, text="📋 Playlist")
        self.notebook.add(self.chapters_tab, text="📑 Chapters")
        self.notebook.add(self.settings_tab, text="⚙️ Settings")
        self.notebook.add(self.cookies_tab, text="🍪 Cookies")
        self.notebook.add(self.downloads_tab, text="⬇️ Downloads")

        # Video Tab with improved layout
        self.video_tab.grid_columnconfigure(1, weight=1)
        self.video_format_label = ttk.Label(self.video_tab, text="Video Format:", font=('', 9, 'bold'))
        self.video_format_label.grid(row=0, column=0, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="w")
        self.video_format_var = tk.StringVar()
        self.video_format_menu = ttk.Combobox(
            self.video_tab, 
            textvariable=self.video_format_var, 
            state="readonly", 
            width=50,
            font=('', 9)
        )
        self.video_format_menu.grid(row=0, column=1, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.video_format_menu, "Select the video quality and format to download")

        # Audio Tab with improved layout
        self.audio_tab.grid_columnconfigure(1, weight=1)
        self.audio_format_label = ttk.Label(self.audio_tab, text="Audio Format:", font=('', 9, 'bold'))
        self.audio_format_label.grid(row=0, column=0, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="w")
        self.audio_format_var = tk.StringVar()
        self.audio_format_menu = ttk.Combobox(
            self.audio_tab, 
            textvariable=self.audio_format_var, 
            state="readonly", 
            width=50,
            font=('', 9)
        )
        self.audio_format_menu.grid(row=0, column=1, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.audio_format_menu, "Select the audio quality and format (used when video has no audio)")

        # Subtitle Tab with improved layout
        self.subtitle_tab.grid_columnconfigure(1, weight=1)
        self.subtitle_lang_label = ttk.Label(self.subtitle_tab, text="Language:", font=('', 9, 'bold'))
        self.subtitle_lang_label.grid(row=0, column=0, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="w")
        self.subtitle_lang_var = tk.StringVar()
        self.subtitle_lang_menu = ttk.Combobox(
            self.subtitle_tab, 
            textvariable=self.subtitle_lang_var, 
            state="readonly",
            font=('', 9)
        )
        self.subtitle_lang_menu.grid(row=0, column=1, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.subtitle_lang_menu, "Select subtitle language (Auto = automatic captions)")
        
        self.subtitle_format_label = ttk.Label(self.subtitle_tab, text="Format:", font=('', 9, 'bold'))
        self.subtitle_format_label.grid(row=0, column=2, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="e")
        self.subtitle_format_var = tk.StringVar(value="srt")
        self.subtitle_format_menu = ttk.Combobox(
            self.subtitle_tab, 
            textvariable=self.subtitle_format_var, 
            values=["srt", "vtt", "ass"],
            state="readonly",
            width=10,
            font=('', 9)
        )
        self.subtitle_format_menu.grid(row=0, column=3, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="w")
        self._create_tooltip(self.subtitle_format_menu, "Subtitle file format: SRT (standard), VTT (WebVTT), ASS (Advanced)")

        # Playlist Tab with improved layout
        self.playlist_var = tk.BooleanVar()
        self.playlist_check = ttk.Checkbutton(
            self.playlist_tab, 
            text="Download entire playlist", 
            variable=self.playlist_var
        )
        self.playlist_check.grid(row=0, column=0, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="w")
        self._create_tooltip(self.playlist_check, "If checked, downloads all videos in the playlist")

        # Chapters Tab with improved layout
        self.chapters_var = tk.BooleanVar()
        self.chapters_check = ttk.Checkbutton(
            self.chapters_tab, 
            text="Split video into chapters", 
            variable=self.chapters_var
        )
        self.chapters_check.grid(row=0, column=0, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="w")
        self._create_tooltip(self.chapters_check, "If checked, splits the video into separate files for each chapter")

        # Settings Tab with improved layout
        self.settings_tab.grid_columnconfigure(1, weight=1)
        
        self.proxy_label = ttk.Label(self.settings_tab, text="Proxy Server:", font=('', 9, 'bold'))
        self.proxy_label.grid(row=0, column=0, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="w")
        self.proxy_entry = ttk.Entry(
            self.settings_tab, 
            width=40,
            font=('', 9)
        )
        self.proxy_entry.grid(row=0, column=1, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.proxy_entry, "Proxy URL (e.g., http://proxy.example.com:8080). Leave empty for direct connection.")
        
        self.ratelimit_label = ttk.Label(
            self.settings_tab, 
            text="Speed Limit:", 
            font=('', 9, 'bold')
        )
        self.ratelimit_label.grid(row=1, column=0, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="w")
        self.ratelimit_entry = ttk.Entry(
            self.settings_tab, 
            width=40,
            font=('', 9)
        )
        self.ratelimit_entry.grid(row=1, column=1, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.ratelimit_entry, "Download speed limit (e.g., 50K, 4.2M, 1G). Leave empty for unlimited speed.")
        
        # Load saved settings
        saved_proxy = self.config.get('proxy', '')
        saved_ratelimit = self.config.get('rate_limit', '')
        if saved_proxy:
            self.proxy_entry.insert(0, saved_proxy)
        if saved_ratelimit:
            self.ratelimit_entry.insert(0, saved_ratelimit)

        # Cookies Tab with improved layout
        self.cookies_tab.grid_columnconfigure(1, weight=1)
        
        self.cookies_browser_label = ttk.Label(self.cookies_tab, text="Browser:", font=('', 9, 'bold'))
        self.cookies_browser_label.grid(row=0, column=0, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="w")
        self.cookies_browser_var = tk.StringVar()
        self.cookies_browser_menu = ttk.Combobox(
            self.cookies_tab,
            textvariable=self.cookies_browser_var,
            state="readonly",
            values=["", "chrome", "firefox", "brave", "chromium", "edge", "opera", "safari", "vivaldi"],
            font=('', 9)
        )
        self.cookies_browser_menu.grid(row=0, column=1, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.cookies_browser_menu, "Select browser to extract cookies from (for age-restricted or private videos)")

        self.cookies_profile_label = ttk.Label(self.cookies_tab, text="Profile Name:", font=('', 9, 'bold'))
        self.cookies_profile_label.grid(row=1, column=0, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="w")
        self.cookies_profile_entry = ttk.Entry(
            self.cookies_tab, 
            width=40,
            font=('', 9)
        )
        self.cookies_profile_entry.grid(row=1, column=1, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.cookies_profile_entry, "Optional: Specific browser profile name (leave empty for default profile)")

        self.cookies_info_label = ttk.Label(
            self.cookies_tab,
            text="💡 Use cookies from a browser to bypass login or age restrictions.\nSelect a browser and, optionally, a specific profile name.",
            wraplength=500,
            font=('', 8),
            foreground='#666',
            justify='left'
        )
        self.cookies_info_label.grid(row=2, column=0, columnspan=2, padx=UIConstants.ENTRY_PADDING, pady=(UIConstants.DEFAULT_PADDING, UIConstants.ENTRY_PADDING), sticky="w")

        # Downloads Tab with improved layout
        download_frame = ttk.Frame(self.downloads_tab)
        download_frame.pack(fill="both", expand=True, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING)
        
        columns = ("URL", "Status", "Size", "Speed", "ETA")
        self.download_queue_tree = ttk.Treeview(download_frame, columns=columns, show="headings", height=10)
        self.download_queue_tree.heading("URL", text="URL")
        self.download_queue_tree.column("URL", width=350, anchor="w")
        self.download_queue_tree.heading("Status", text="Status")
        self.download_queue_tree.column("Status", width=120, anchor="center")
        self.download_queue_tree.heading("Size", text="Size")
        self.download_queue_tree.column("Size", width=100, anchor="center")
        self.download_queue_tree.heading("Speed", text="Speed")
        self.download_queue_tree.column("Speed", width=100, anchor="center")
        self.download_queue_tree.heading("ETA", text="ETA")
        self.download_queue_tree.column("ETA", width=100, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(download_frame, orient="vertical", command=self.download_queue_tree.yview)
        self.download_queue_tree.configure(yscrollcommand=scrollbar.set)
        self.download_queue_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.context_menu = tk.Menu(self.master, tearoff=0)
        self.context_menu.add_command(label="Cancel", command=self.cancel_download_item)
        self.context_menu.add_command(label="Remove", command=self.remove_from_queue)
        self.context_menu.add_command(label="Open File Location", command=self.open_file_location)
        self.download_queue_tree.bind("<Button-3>", self.show_context_menu)

        # Output Path with improved layout
        path_frame = ttk.LabelFrame(self.frame, text="💾 Save Location", padding=UIConstants.ENTRY_PADDING)
        path_frame.grid(row=4, column=0, columnspan=4, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        path_frame.grid_columnconfigure(1, weight=1)
        
        self.path_label = ttk.Label(path_frame, text="Path:", font=('', 9, 'bold'))
        self.path_label.grid(row=0, column=0, padx=(0, UIConstants.ENTRY_PADDING), pady=UIConstants.ENTRY_PADDING, sticky="w")
        self.path_entry = ttk.Entry(
            path_frame, 
            width=50,
            font=('', 9)
        )
        # Set default path to user's Downloads folder
        default_path = str(Path.home() / "Downloads")
        self.path_entry.insert(0, default_path)
        self.path_entry.grid(row=0, column=1, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.path_entry, "Directory where downloaded files will be saved")
        
        self.browse_button = ttk.Button(
            path_frame, 
            text="📁 Browse...", 
            command=self.browse_path,
            width=15
        )
        self.browse_button.grid(row=0, column=2, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING)

        # Control Buttons with improved layout
        button_frame = ttk.Frame(self.frame)
        button_frame.grid(row=5, column=0, columnspan=4, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.DEFAULT_PADDING, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        button_frame.grid_columnconfigure(2, weight=1)
        button_frame.grid_columnconfigure(3, weight=1)
        
        self.download_button = ttk.Button(
            button_frame, 
            text="➕ Add to Queue", 
            command=self.add_to_queue,
            width=18
        )
        self.download_button.grid(row=0, column=0, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.download_button, "Add the current video to download queue")
        
        self.pause_button = ttk.Button(
            button_frame, 
            text="⏸️ Pause", 
            command=self.toggle_pause_resume, 
            state="disabled",
            width=18
        )
        self.pause_button.grid(row=0, column=1, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.pause_button, "Pause or resume the current download")
        
        self.cancel_button = ttk.Button(
            button_frame, 
            text="❌ Cancel", 
            command=self.cancel_download, 
            state="disabled",
            width=18
        )
        self.cancel_button.grid(row=0, column=2, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.cancel_button, "Cancel the current download")
        
        self.clear_button = ttk.Button(
            button_frame, 
            text="🗑️ Clear", 
            command=self.clear_ui,
            width=18
        )
        self.clear_button.grid(row=0, column=3, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.clear_button, "Clear all input fields and video information")
        
        # Import button in a new row
        button_frame.grid_rowconfigure(1, weight=0)
        self.import_button = ttk.Button(
            button_frame,
            text="📥 Import URLs from File",
            command=self.import_urls_from_file,
            width=18
        )
        self.import_button.grid(row=1, column=0, columnspan=2, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        self._create_tooltip(self.import_button, "Import multiple URLs from a text file (one URL per line). Press Ctrl+I")
        
        # Progress Bar with improved styling
        progress_frame = ttk.LabelFrame(self.frame, text="📊 Download Progress", padding=UIConstants.ENTRY_PADDING)
        progress_frame.grid(row=6, column=0, columnspan=4, padx=UIConstants.ENTRY_PADDING, pady=UIConstants.ENTRY_PADDING, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            orient="horizontal", 
            length=300, 
            mode="determinate",
            style="TProgressbar"
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, UIConstants.ENTRY_PADDING))
        
        self.status_label = ttk.Label(
            progress_frame, 
            text="Ready",
            font=('', 9),
            foreground='#666'
        )
        self.status_label.grid(row=1, column=0, sticky="w")

        # Loading animation
        self.loading_animation_label = ttk.Label(self.info_frame, text="Fetching...")
        self.loading_animation_label.grid(row=1, column=1, sticky="w")
        self.loading_animation_label.grid_remove()

        # Set initial theme based on config
        theme = "dark" if self.dark_mode.get() else "light"
        logger.debug("Setting initial theme to %s", theme)

        # Style configuration - removed custom button styling to use theme defaults
        # The sv_ttk theme will handle button styling automatically

    def _setup_main_window(self) -> None:
        """Configure the main window."""
        self.master.title("YTDownloader - Advanced YouTube Video Downloader")
        self.master.geometry(f"{UIConstants.WINDOW_MIN_WIDTH}x{UIConstants.WINDOW_MIN_HEIGHT}")
        self.master.minsize(UIConstants.WINDOW_MIN_WIDTH, UIConstants.WINDOW_MIN_HEIGHT)
        
        # Store initial geometry
        self.master.update_idletasks()
        self.normal_geometry = self.master.geometry()

        # Bind F11 for fullscreen toggle
        self.master.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.master.bind('<Escape>', lambda e: self.exit_fullscreen() if self.is_fullscreen else None)

        try:
            icon_path = Path(__file__).parent / "icon.ico"
            if icon_path.exists():
                self.master.iconbitmap(str(icon_path))
        except Exception:
            pass  # Icon not critical

    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget."""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(
                tooltip, 
                text=text, 
                background="#ffffe0", 
                relief="solid", 
                borderwidth=1,
                font=('', 8),
                padding=5,
                wraplength=300
            )
            label.pack()
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)

    def toggle_theme(self) -> None:
        """Toggle between light and dark theme and persist preference."""
        sv_ttk.toggle_theme()
        self.dark_mode.set(not self.dark_mode.get())
        # Save theme preference
        self.config['dark_mode'] = self.dark_mode.get()
        save_config(self.config)
        logger.info(f"Theme changed to {'dark' if self.dark_mode.get() else 'light'}")

    def process_ui_queue(self):
        processed = 0
        try:
            while True:
                task, kwargs = self.ui_queue.get_nowait()
                task(**kwargs)
                processed += 1
        except queue.Empty:
            pass
        if processed:
            logger.debug("Processed %d UI callbacks", processed)
        self.master.after(UIConstants.QUEUE_POLL_INTERVAL, self.process_ui_queue)

    def _safe_clear_ui(self):
        """Safely clear UI only if no download is in progress."""
        if self.is_downloading() or self.cancel_token:
            logger.debug("Skipping UI clear - download in progress")
            return
        self.clear_ui()
    
    def clear_ui(self):
        """Clear UI state - should only be called when safe."""
        logger.debug("Clearing UI state")
        # Don't clear if download is active
        if self.is_downloading():
            logger.warning("Attempted to clear UI while download active - ignoring")
            return
        
        self.url_entry.delete(0, tk.END)
        self.title_label.config(text="Title: N/A")
        self.duration_label.config(text="Duration: N/A")
        self.thumbnail_label.config(image=None)
        self.thumbnail_label.image = None
        self.video_format_menu.set('')
        self.video_format_menu.config(values=[])
        self.audio_format_menu.set('')
        self.audio_format_menu.config(values=[])
        self._video_streams = []
        self._audio_streams = []
        self.subtitle_lang_menu.set('')
        self.subtitle_lang_menu.config(values=[])
        self.status_label.config(text="Ready")
        self.progress_bar['value'] = 0
        self.playlist_var.set(False)
        self.chapters_var.set(False)

    def fetch_info(self):
        """Fetch and display video information in a separate thread."""
        url = self.url_entry.get().strip()
        logger.info("Fetch info requested for URL='%s'", url)
        if not url:
            messagebox.showwarning("Input Error", "Please enter a valid YouTube URL.")
            logger.warning("Fetch info aborted: empty URL")
            return

        if not validate_url(url):
            messagebox.showwarning("Invalid URL", "Please enter a valid URL starting with http:// or https://")
            logger.warning("Fetch info aborted: invalid URL '%s'", url)
            return

        self.loading_animation_label.grid()
        self.fetch_button.config(state="disabled")
        self.status_label.config(text="Fetching video information...")
        logger.debug("Starting background fetch thread for %s", url)

        def _fetch():
            try:
                cookies_browser = self.cookies_browser_var.get()
                cookies_profile = self.cookies_profile_entry.get().strip()

                info = get_video_info(
                    url,
                    cookies_from_browser=cookies_browser if cookies_browser else None,
                    cookies_from_browser_profile=cookies_profile if cookies_profile else None
                )
                if not info:
                    raise yt_dlp.utils.DownloadError("Failed to fetch video information.")

                title = info.get('title', 'N/A')
                duration = info.get('duration', 'N/A')
                logger.info("Video info retrieved: title='%s', duration='%s'", title, duration)

                self.ui_queue.put((self.title_label.config, {'text': f"Title: {title}"}))
                self.ui_queue.put((self.duration_label.config, {'text': f"Duration: {duration}"}))
                self.ui_queue.put((self.status_label.config, {'text': "Video info loaded successfully."}))

                self._video_streams = info.get('video_streams', [])
                self._audio_streams = info.get('audio_streams', [])

                # Update subtitle language menu
                subtitles = info.get('subtitles', {})
                if subtitles:
                    subtitle_langs = list(subtitles.keys())
                    self.ui_queue.put((self.subtitle_lang_menu.config, {'values': subtitle_langs}))
                    self.ui_queue.put((self.subtitle_lang_menu.set, {'value': ''}))
                    logger.info("Subtitle languages available: %s", subtitle_langs)
                else:
                    # No subtitles available
                    self.ui_queue.put((self.subtitle_lang_menu.config, {'values': ['No subtitles available']}))
                    self.ui_queue.put((self.subtitle_lang_menu.set, {'value': 'No subtitles available'}))
                    logger.warning("No subtitles found for this video")

                # Build video format strings with proper file size handling
                video_formats = []
                for s in self._video_streams:
                    filesize_str = format_file_size(s.get('filesize'))
                    fmt_str = (
                        f"{s.get('resolution', 'N/A')}@{s.get('fps', 'N/A')}fps "
                        f"({s.get('ext', 'N/A').upper()}) - "
                        f"V:{s.get('vcodec', 'N/A')} A:{s.get('acodec', 'N/A')} "
                        f"({filesize_str}) - {s.get('format_id', 'N/A')}"
                    )
                    video_formats.append(fmt_str)

                self.ui_queue.put((self.video_format_menu.config, {'values': video_formats}))
                if video_formats:
                    self.ui_queue.put((self.video_format_menu.set, {'value': video_formats[0]}))
                logger.debug("Configured %d video format options", len(video_formats))

                # Build audio format strings with proper file size handling
                audio_formats = []
                for s in self._audio_streams:
                    filesize_str = format_file_size(s.get('filesize'))
                    fmt_str = (
                        f"{s.get('abr', 'N/A')}kbps ({s.get('ext', 'N/A').upper()}) - "
                        f"A:{s.get('acodec', 'N/A')} ({filesize_str}) - {s.get('format_id', 'N/A')}"
                    )
                    audio_formats.append(fmt_str)

                self.ui_queue.put((self.audio_format_menu.config, {'values': audio_formats}))
                if audio_formats:
                    self.ui_queue.put((self.audio_format_menu.set, {'value': audio_formats[0]}))
                logger.debug("Configured %d audio format options", len(audio_formats))

                # Load and display thumbnail
                if info.get('thumbnail'):
                    logger.debug("Attempting to download thumbnail from %s", info['thumbnail'])
                    try:
                        response = requests.get(info['thumbnail'], timeout=5)
                        response.raise_for_status()
                        img_data = response.content
                        img = Image.open(BytesIO(img_data))
                        img.thumbnail(UIConstants.THUMBNAIL_SIZE)
                        try:
                            photo = ImageTk.PhotoImage(img)
                            self.ui_queue.put((self.thumbnail_label.config, {'image': photo}))
                            self.thumbnail_label.image = photo
                        except Exception as img_error:  # pragma: no cover - depends on runtime environment
                            logger.debug("Thumbnail rendering skipped: %s", img_error)
                    except requests.exceptions.RequestException as e:
                        logger.warning(f"Failed to fetch thumbnail: {e}")
            except yt_dlp.utils.DownloadError as e:
                self.handle_error("Invalid URL or network error", e)
            except Exception as e:
                logger.exception("Unexpected error during fetch_info")
                self.handle_error("An unexpected error occurred", e)
            finally:
                self.ui_queue.put((self.loading_animation_label.grid_remove, {}))
                self.ui_queue.put((self.fetch_button.config, {'state': "normal"}))
                logger.debug("Fetch thread for %s completed", url)

        self.fetch_thread = threading.Thread(target=_fetch, daemon=True)
        self.fetch_thread.start()
        logger.debug("Fetch thread started for %s", url)

    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            logger.info("Output path selected: %s", path)

    def progress_hook(self, d, item):
        """Update progress bar and status based on download progress."""
        logger.debug("Progress hook event: status=%s", d.get('status'))
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes is not None and total_bytes > 0:
                downloaded_bytes = d.get('downloaded_bytes', 0)
                if downloaded_bytes is not None:
                    percentage = min((downloaded_bytes / total_bytes) * 100, 100)
                    self.ui_queue.put((self.progress_bar.config, {'value': percentage}))

                # Format speed for display
                speed = d.get('speed')
                if speed and isinstance(speed, (int, float)):
                    speed_str = format_file_size(speed) + "/s"
                else:
                    speed_str = "N/A"
                
                # Format ETA for display
                eta = d.get('eta')
                if eta and isinstance(eta, (int, float)) and eta > 0:
                    eta_str = f"{int(eta)}s"
                else:
                    eta_str = "N/A"

                item['size'] = format_file_size(total_bytes)
                item['speed'] = speed_str
                item['eta'] = eta_str
                
                # Update status with more details
                status_text = f"Downloading... {format_file_size(downloaded_bytes)} / {format_file_size(total_bytes)} ({speed_str})"
                self.ui_queue.put((self.status_label.config, {'text': status_text}))
                self.ui_queue.put((self.update_download_queue_list, {}))

        elif d['status'] == 'finished':
            self.ui_queue.put((self.progress_bar.config, {'value': 100}))
            self.ui_queue.put((self.status_label.config, {'text': "✅ Download complete!"}))
            item['status'] = 'Completed'
            self.ui_queue.put((self.update_download_queue_list, {}))
            logger.info("Download finished for %s", item.get('url'))

    def add_to_queue(self):
        """Add a download to the queue with validation."""
        url = self.url_entry.get().strip()
        logger.info("Queueing request for URL='%s'", url)
        if not url:
            messagebox.showwarning("Input Error", "Please enter a URL.")
            logger.warning("Queueing aborted: empty URL")
            return

        if not validate_url(url):
            messagebox.showwarning("Invalid URL", "Please enter a valid URL starting with http:// or https://")
            logger.warning("Queueing aborted: invalid URL '%s'", url)
            return

        video_format = self.video_format_var.get()
        if not video_format:
            messagebox.showwarning("Format Error", "Please fetch video info and select a video format.")
            logger.warning("Queueing aborted: missing video format for %s", url)
            return

        # Validate proxy format
        proxy = self.proxy_entry.get().strip()
        if proxy and not validate_proxy(proxy):
            messagebox.showerror(
                "Invalid Proxy", 
                "Invalid proxy format.\n\nExpected format: protocol://host:port\nExample: http://proxy.example.com:8080"
            )
            logger.warning("Queueing aborted: invalid proxy '%s'", proxy)
            return

        # Validate rate limit format
        rate_limit = self.ratelimit_entry.get().strip()
        if rate_limit and not validate_rate_limit(rate_limit):
            messagebox.showerror(
                "Invalid Rate Limit", 
                "Invalid rate limit format.\n\nValid formats:\n• 50K (50 kilobytes per second)\n• 4.2M (4.2 megabytes per second)\n• 1G (1 gigabyte per second)"
            )
            logger.warning("Queueing aborted: invalid rate limit '%s'", rate_limit)
            return
        
        # Save settings to config
        self.config['proxy'] = proxy
        self.config['rate_limit'] = rate_limit
        save_config(self.config)

        # Validate output path
        output_path = self.path_entry.get().strip() or '.'
        if not Path(output_path).exists():
            messagebox.showerror("Invalid Path", f"Output directory does not exist: {output_path}")
            logger.warning("Queueing aborted: output path missing '%s'", output_path)
            return

        audio_format = self.audio_format_var.get()
        subtitle_lang = self.subtitle_lang_var.get()
        # Treat "No subtitles available" as None
        if subtitle_lang == 'No subtitles available' or not subtitle_lang:
            subtitle_lang = None
        elif subtitle_lang.endswith(' (Auto)'):
            # Strip "(Auto)" suffix for yt-dlp - it only needs the language code
            subtitle_lang = subtitle_lang[:-7].strip()
        subtitle_format = self.subtitle_format_var.get()
        playlist = self.playlist_var.get()
        split_chapters = self.chapters_var.get()

        cookies_browser = self.cookies_browser_var.get()
        cookies_profile = self.cookies_profile_entry.get().strip()

        download_item = {
            "url": url,
            "video_format": video_format,
            "audio_format": audio_format,
            "subtitle_lang": subtitle_lang,
            "subtitle_format": subtitle_format,
            "output_path": output_path,
            "playlist": playlist,
            "split_chapters": split_chapters,
            "proxy": proxy or None,
            "rate_limit": rate_limit or None,
            "cookies_browser": cookies_browser if cookies_browser else None,
            "cookies_profile": cookies_profile if cookies_profile else None,
            "status": "Queued",
            "size": "N/A",
            "speed": "N/A",
            "eta": "N/A"
        }

        self.download_queue.append(download_item)
        logger.info(f"Added download to queue: {url}")
        self.update_download_queue_list()
        self.status_label.config(text=f"✅ Added to queue ({len(self.download_queue)} item{'s' if len(self.download_queue) != 1 else ''})")

        if not self.is_downloading():
            self.process_download_queue()

    def import_urls_from_file(self, event=None):
        """Import multiple URLs from a text file and add them to the queue."""
        # Open file dialog to select text file
        file_path = filedialog.askopenfilename(
            title="Select URLs File",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            logger.debug("File import cancelled by user")
            return
        
        try:
            # Read file and parse URLs
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Parse and validate URLs
            valid_urls = []
            invalid_lines = []
            
            for line_num, line in enumerate(lines, 1):
                url = line.strip()
                # Skip empty lines and comments (lines starting with #)
                if not url or url.startswith('#'):
                    continue
                
                # Validate URL
                if validate_url(url):
                    valid_urls.append(url)
                else:
                    invalid_lines.append((line_num, url))
            
            if not valid_urls:
                messagebox.showwarning(
                    "No Valid URLs",
                    f"No valid URLs found in the file.\n\n"
                    f"Invalid/empty lines: {len(invalid_lines)}\n\n"
                    f"Please ensure each line contains a valid URL starting with http:// or https://"
                )
                return
            
            # Get current settings
            proxy = self.proxy_entry.get().strip() or None
            rate_limit = self.ratelimit_entry.get().strip() or None
            output_path = self.path_entry.get().strip() or str(Path.home() / "Downloads")
            audio_format = self.audio_format_var.get() or "best"
            subtitle_lang = self.subtitle_lang_var.get()
            if subtitle_lang == 'No subtitles available' or not subtitle_lang:
                subtitle_lang = None
            elif subtitle_lang.endswith(' (Auto)'):
                subtitle_lang = subtitle_lang[:-7].strip()
            subtitle_format = self.subtitle_format_var.get()
            playlist = self.playlist_var.get()
            split_chapters = self.chapters_var.get()
            cookies_browser = self.cookies_browser_var.get() if self.cookies_browser_var.get() else None
            cookies_profile = self.cookies_profile_entry.get().strip() if self.cookies_profile_entry.get().strip() else None
            
            # Validate output path
            if not Path(output_path).exists():
                messagebox.showerror("Invalid Path", f"Output directory does not exist: {output_path}")
                return
            
            # Add all valid URLs to queue with "best" format (will auto-select best quality)
            added_count = 0
            for url in valid_urls:
                download_item = {
                    "url": url,
                    "video_format": "best",  # Use "best" format for batch imports
                    "audio_format": audio_format,
                    "subtitle_lang": subtitle_lang,
                    "subtitle_format": subtitle_format,
                    "output_path": output_path,
                    "playlist": playlist,
                    "split_chapters": split_chapters,
                    "proxy": proxy,
                    "rate_limit": rate_limit,
                    "cookies_browser": cookies_browser,
                    "cookies_profile": cookies_profile,
                    "status": "Queued",
                    "size": "N/A",
                    "speed": "N/A",
                    "eta": "N/A"
                }
                self.download_queue.append(download_item)
                added_count += 1
                logger.info(f"Imported URL to queue: {url}")
            
            # Update UI
            self.update_download_queue_list()
            
            # Show summary
            summary_msg = f"✅ Successfully imported {added_count} URL{'s' if added_count != 1 else ''} to queue."
            if invalid_lines:
                summary_msg += f"\n\n⚠️ Skipped {len(invalid_lines)} invalid line(s)."
                if len(invalid_lines) <= 10:  # Show details if not too many
                    invalid_details = "\n".join([f"Line {num}: {url[:50]}..." if len(url) > 50 else f"Line {num}: {url}" 
                                                 for num, url in invalid_lines[:10]])
                    summary_msg += f"\n\nInvalid lines:\n{invalid_details}"
                    if len(invalid_lines) > 10:
                        summary_msg += f"\n... and {len(invalid_lines) - 10} more"
            
            self.status_label.config(text=summary_msg)
            messagebox.showinfo("Import Complete", summary_msg)
            
            # Start processing queue if not already downloading
            if not self.is_downloading():
                self.process_download_queue()
                
        except FileNotFoundError:
            messagebox.showerror("File Not Found", f"The file could not be found:\n{file_path}")
            logger.error(f"File not found: {file_path}")
        except PermissionError:
            messagebox.showerror("Permission Denied", f"Permission denied to read the file:\n{file_path}")
            logger.error(f"Permission denied: {file_path}")
        except UnicodeDecodeError as e:
            messagebox.showerror("Encoding Error", f"Could not read the file. Please ensure it's a UTF-8 text file.\n\nError: {e}")
            logger.error(f"Encoding error reading file: {file_path}, error: {e}")
        except Exception as e:
            messagebox.showerror("Import Error", f"An error occurred while importing URLs:\n\n{type(e).__name__}: {e}")
            logger.exception(f"Error importing URLs from file: {file_path}")

    def update_download_queue_list(self):
        logger.debug("Refreshing download queue list with %d item(s)", len(self.download_queue))
        for i in self.download_queue_tree.get_children():
            self.download_queue_tree.delete(i)
        for i, item in enumerate(self.download_queue):
            try:
                values = (
                    item.get('url', 'N/A'),
                    item.get('status', 'N/A'),
                    item.get('size', 'N/A'),
                    item.get('speed', 'N/A'),
                    item.get('eta', 'N/A')
                )
                self.download_queue_tree.insert("", "end", iid=i, values=values)
            except KeyError:
                # Handle old download items that don't have the new keys
                self.download_queue_tree.insert("", "end", iid=i, values=(item['url'], item['status'], "N/A", "N/A", "N/A"))

    def is_downloading(self):
        downloading = any(item['status'] == 'Downloading' for item in self.download_queue)
        logger.debug("is_downloading -> %s", downloading)
        return downloading

    def process_download_queue(self):
        logger.debug("Processing download queue")
        if not self.is_downloading():
            for item in self.download_queue:
                if item['status'] == 'Queued':
                    logger.info("Starting queued download for %s", item.get('url'))
                    self.start_download_thread(item)
                    break

    def start_download_thread(self, item):
        logger.debug("Spawning download thread for %s", item.get('url'))
        item['status'] = 'Downloading'
        self.current_download_item = item
        self.is_paused = False  # Reset pause state for new download
        self.update_download_queue_list()
        self.download_button.config(state="disabled")
        self.pause_button.config(state="normal", text="Pause")
        self.cancel_button.config(state="normal")
        self.status_label.config(text=f"Downloading {item['url']}...")
        self.progress_bar['value'] = 0
        thread = threading.Thread(target=self.download, args=(item,))
        thread.daemon = True
        thread.start()

    def _extract_format_id(self, format_string: str) -> Optional[str]:
        """Safely extract format ID from format string."""
        if not format_string:
            logger.debug("No format string provided for extraction")
            return None
        # Format ID is at the end after ' - '
        parts = format_string.rsplit(' - ', 1)
        format_id = parts[-1].strip() if parts else None
        logger.debug("Extracted format id '%s' from '%s'", format_id, format_string)
        return format_id

    def download(self, item: Dict[str, Any]) -> None:
        """Download video with proper error handling and cancellation."""
        # Create CancelToken with callback to sync pause state
        self.cancel_token = CancelToken(pause_callback=lambda: self.is_paused)
        logger.debug("Download routine entered for %s", item.get('url'))
        try:
            self._handle_download_logic(item)
        except yt_dlp.utils.DownloadError as e:
            if "Download cancelled by user" in str(e):
                item['status'] = 'Cancelled'
                self.ui_queue.put((self.status_label.config, {'text': f"Download cancelled: {item.get('url', 'Unknown')}"}))
                logger.info(f"Download cancelled: {item['url']}")
            else:
                item['status'] = 'Error'
                logger.error(f"Download error for {item['url']}: {e}")
                self.handle_error(f"Download failed for {item['url']}", e)
        except Exception as e:
            item['status'] = 'Error'
            logger.exception(f"Unexpected error during download of {item['url']}")
            self.handle_error(f"An unexpected error occurred", e)
        finally:
            # Only clear UI if this was the current download and it completed successfully
            should_clear_ui = (self.current_download_item == item and item['status'] == 'Completed')
            
            self.cancel_token = None
            self.current_download_item = None
            self.is_paused = False  # Reset pause state
            
            self.ui_queue.put((self.download_button.config, {'state': "normal"}))
            self.ui_queue.put((self.pause_button.config, {'state': "disabled", 'text': "Pause"}))
            self.ui_queue.put((self.cancel_button.config, {'state': "disabled"}))
            self.ui_queue.put((self.update_download_queue_list, {}))
            
            # Only process queue if not cancelled and not the last item
            if item['status'] != 'Cancelled':
                self.ui_queue.put((self.process_download_queue, {}))
            
            # Only clear UI for successful completion, and only once
            if should_clear_ui:
                self.ui_queue.put((self._safe_clear_ui, {}))
            
            logger.debug("Download routine exited for %s with status %s", item.get('url'), item.get('status'))
    def _handle_download_logic(self, item: Dict[str, Any]) -> None:
        """Helper method to handle the core download logic."""
        # Initial pause check - the CancelToken.check() will handle pause during download
        if self.is_paused:
            logger.debug("Download starting in paused state for %s", item.get('url'))
            self.cancel_token.pause()

        # Handle "best" format (used for batch imports)
        video_format_str = item.get('video_format', 'best')
        if video_format_str == 'best':
            # Use "best" format directly - yt-dlp will select the best quality
            video_format = 'best'
            logger.info(f"Starting download: {item['url']} with format 'best' (auto-select)")
        else:
            # Extract format IDs safely for manually selected formats
            video_format_id = self._extract_format_id(video_format_str)
            if not video_format_id:
                raise ValueError(f"Could not extract video format ID from: {video_format_str}")

            audio_format_id = self._extract_format_id(item.get('audio_format', ''))

            # Check if video stream has audio
            video_stream = next((s for s in self._video_streams if s.get('format_id') == video_format_id), None)

            if video_stream and video_stream.get('acodec') != 'none':
                video_format = video_format_id
            else:
                if not audio_format_id:
                    raise ValueError("Could not extract audio format ID.")
                video_format = f"{video_format_id}+{audio_format_id}"

            logger.info(f"Starting download: {item['url']} with format {video_format}")

        download_video(
            item['url'],
            self.progress_hook,
            item,
            item['playlist'],
            video_format,
            item['output_path'],
            item['subtitle_lang'],
            item['subtitle_format'],
            item['split_chapters'],
            item['proxy'],
            item['rate_limit'],
            self.cancel_token,
            item.get('cookies_browser'),
            item.get('cookies_profile')
        )
        item['status'] = 'Completed'
        logger.info(f"Download completed: {item['url']}")

    def handle_error(self, message: str, error: Exception) -> None:
        """Handle and display errors with improved user-friendly messages."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        logger.error(f"{message}: {error_type} - {error_msg}")
        
        # Create user-friendly error message
        user_message = f"{message}\n\n"
        if "network" in error_msg.lower() or "connection" in error_msg.lower():
            user_message += "Network Error: Please check your internet connection and try again."
        elif "format" in error_msg.lower() or "codec" in error_msg.lower():
            user_message += "Format Error: The selected format may not be available. Try selecting a different format."
        elif "private" in error_msg.lower() or "unavailable" in error_msg.lower():
            user_message += "Video Unavailable: This video may be private, restricted, or removed."
        else:
            user_message += f"Error: {error_msg[:200]}"  # Limit error message length
        
        user_message += "\n\nFor detailed information, check ytdownloader.log"
        
        messagebox.showerror("Error", user_message)
        self.ui_queue.put((
            self.status_label.config,
            {'text': "❌ Error occurred. Check log for details.", 'foreground': '#d32f2f'}
        ))

    def cancel_download(self):
        """Cancel the current download with user confirmation."""
        if not self.cancel_token:
            messagebox.showinfo("Info", "No active download to cancel.")
            return
        
        if self.current_download_item:
            url = self.current_download_item.get('url', 'Unknown')
            if messagebox.askyesno("Confirm Cancellation", 
                                  f"Are you sure you want to cancel the download?\n\nURL: {url}"):
                self.cancel_token.cancel()
                self.is_paused = False  # Reset pause state
                self.pause_button.config(state="disabled", text="Pause")
                self.status_label.config(text="Cancelling download...")
                logger.info("Cancel request confirmed for active download: %s", url)
            else:
                logger.debug("Cancel request cancelled by user")
        else:
            self.cancel_token.cancel()
            logger.info("Cancel request issued for active download")

    def toggle_pause_resume(self):
        """Toggle pause/resume state with proper synchronization."""
        if not self.cancel_token:
            messagebox.showinfo("Info", "No active download to pause/resume.")
            return
        
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.cancel_token.pause()
            self.pause_button.config(text="Resume")
            if self.current_download_item:
                self.status_label.config(text=f"Download paused: {self.current_download_item.get('url', 'Unknown')}")
            else:
                self.status_label.config(text="Download paused.")
            logger.info("Download paused by user")
        else:
            self.cancel_token.resume()
            self.pause_button.config(text="Pause")
            if self.current_download_item:
                self.status_label.config(text=f"Resuming download: {self.current_download_item.get('url', 'Unknown')}...")
            else:
                self.status_label.config(text="Resuming download...")
            logger.info("Download resumed by user")

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode (F11)."""
        self.is_fullscreen = not self.is_fullscreen
        
        if self.is_fullscreen:
            # Store current geometry before going fullscreen
            self.normal_geometry = self.master.geometry()
            
            # Use attributes('-fullscreen', True) which works properly on Windows
            # This is the standard Tkinter way to go fullscreen
            self.master.attributes('-fullscreen', True)
            
            # Ensure the main frame expands to fill the entire window
            self.frame.grid(row=0, column=0, sticky="nsew")
            self.master.grid_columnconfigure(0, weight=1, minsize=0)
            self.master.grid_rowconfigure(0, weight=1, minsize=0)
            
            # Force layout update to ensure everything expands
            self.master.update_idletasks()
            
            # Get actual screen dimensions for logging
            screen_width = self.master.winfo_width()
            screen_height = self.master.winfo_height()
            logger.info("Entered fullscreen mode: %dx%d", screen_width, screen_height)
        else:
            # Exit fullscreen
            self.master.attributes('-fullscreen', False)
            
            # Restore normal geometry
            if self.normal_geometry:
                self.master.geometry(self.normal_geometry)
            else:
                self.master.geometry(f"{UIConstants.WINDOW_MIN_WIDTH}x{UIConstants.WINDOW_MIN_HEIGHT}")
            
            # Force layout update
            self.master.update_idletasks()
            logger.info("Exited fullscreen mode")
    
    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode (Escape)."""
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.master.attributes('-fullscreen', False)
            
            if self.normal_geometry:
                self.master.geometry(self.normal_geometry)
            else:
                self.master.geometry(f"{UIConstants.WINDOW_MIN_WIDTH}x{UIConstants.WINDOW_MIN_HEIGHT}")
            
            self.master.update_idletasks()
            logger.info("Exited fullscreen mode via Escape")

    def show_about(self):
        about_text = (
            "YTDownloader\n\n"
            "Version: 1.0\n\n"
            "Advanced YouTube Video Downloader\n"
            "Built with Python and Tkinter\n\n"
            "Features:\n"
            "• Download videos in various formats\n"
            "• Batch import from text files\n"
            "• Subtitle support\n"
            "• Playlist and chapter support\n"
            "• Proxy and rate limiting\n\n"
            "Keyboard Shortcuts:\n"
            "• F11: Toggle Fullscreen\n"
            "• Escape: Exit Fullscreen\n"
            "• Ctrl+I: Import URLs from File\n"
            "• Enter: Fetch video info (in URL field)"
        )
        messagebox.showinfo("About", about_text)
        logger.debug("Displayed About dialog")

    def show_context_menu(self, event):
        selection = self.download_queue_tree.identify_row(event.y)
        if selection:
            self.download_queue_tree.selection_set(selection)
            self.context_menu.post(event.x_root, event.y_root)
            logger.debug("Context menu shown for selection %s", selection)

    def remove_from_queue(self) -> None:
        """Remove selected item(s) from download queue."""
        try:
            selection = self.download_queue_tree.selection()
            if not selection:
                messagebox.showwarning("Selection Error", "Please select an item to remove.")
                return

            # Get indices and sort in reverse to avoid index shifting issues
            indices_to_remove = sorted([int(item_id) for item_id in selection], reverse=True)

            for item_index in indices_to_remove:
                if 0 <= item_index < len(self.download_queue):
                    removed_item = self.download_queue.pop(item_index)
                    logger.info(f"Removed from queue: {removed_item.get('url', 'Unknown')}")
                else:
                    messagebox.showerror("Error", f"Invalid queue item index: {item_index}")
        
            self.update_download_queue_list()
            self.status_label.config(text=f"Removed {len(indices_to_remove)} item(s). Queue size: {len(self.download_queue)}")

        except (IndexError, ValueError) as e:
            logger.error(f"Error removing from queue: {e}")
            messagebox.showerror("Error", "Failed to remove item from queue.")

    def cancel_download_item(self) -> None:
        """Cancel or mark selected download item as cancelled."""
        try:
            selection = self.download_queue_tree.selection()
            if not selection:
                messagebox.showwarning("Selection Error", "Please select an item to cancel.")
                logger.warning("Cancel download requested without selection")
                return

            item_index = int(selection[0])
            if 0 <= item_index < len(self.download_queue):
                item = self.download_queue[item_index]
                if item['status'] == 'Downloading':
                    if messagebox.askyesno("Confirm", "Cancel the current download?"):
                        self.cancel_download()
                        logger.info("User confirmed cancellation of active download")
                else:
                    item['status'] = 'Cancelled'
                    logger.info(f"Cancelled queued download: {item.get('url', 'Unknown')}")
                    self.update_download_queue_list()
            else:
                messagebox.showerror("Error", "Invalid queue item index.")
                logger.error("Cancel download failed due to invalid index %s", item_index)
        except (IndexError, ValueError) as e:
            logger.error(f"Error cancelling download item: {e}")
            messagebox.showerror("Error", "Failed to cancel download item.")

    def open_file_location(self) -> None:
        """Open the output folder for the selected download."""
        try:
            selection = self.download_queue_tree.selection()
            if not selection:
                messagebox.showwarning("Selection Error", "Please select an item to open.")
                logger.warning("Open file location requested without selection")
                return

            item_index = int(selection[0])
            if 0 <= item_index < len(self.download_queue):
                item = self.download_queue[item_index]
                output_path = item.get('output_path', '.')
                logger.debug("Attempting to open file location %s", output_path)

                if not Path(output_path).exists():
                    messagebox.showerror("Error", f"Output directory does not exist: {output_path}")
                    logger.error("Open file location failed; missing path %s", output_path)
                    return

                try:
                    if sys.platform == "win32":
                        os.startfile(output_path)
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", output_path], stderr=subprocess.DEVNULL)
                    else:
                        subprocess.Popen(["xdg-open", output_path], stderr=subprocess.DEVNULL)
                except Exception as e:
                    logger.error(f"Failed to open file location: {e}")
                    messagebox.showerror("Error", f"Failed to open folder: {e}")
            else:
                messagebox.showerror("Error", "Invalid queue item index.")
                logger.error("Open file location failed due to invalid index %s", item_index)
        except (IndexError, ValueError) as e:
            logger.error(f"Error opening file location: {e}")
            messagebox.showerror("Error", "Failed to open file location.")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = YTDownloaderGUI(root)
        if not _HEADLESS:
            sv_ttk.set_theme("dark" if app.dark_mode.get() else "light")
        root.mainloop()
        logger.info("YTDownloader closed")
    except Exception as e:
        logger.exception("Fatal error in main")
        messagebox.showerror("Fatal Error", f"An unexpected error occurred:\n{e}")
