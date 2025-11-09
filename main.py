import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sv_ttk
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
from dataclasses import dataclass

class CancelToken:
    """Token for managing download cancellation and pause/resume."""
    def __init__(self):
        self.cancelled = False
        self.is_paused = False

    def cancel(self):
        """Mark the download as cancelled."""
        self.cancelled = True

    def check(self, d):
        """Check if download should be cancelled or paused."""
        if self.cancelled:
            raise yt_dlp.utils.DownloadError("Download cancelled by user.")
        while self.is_paused:
            time.sleep(0.5)
            if self.cancelled:
                raise yt_dlp.utils.DownloadError("Download cancelled by user.")

# Configure logging
logging.basicConfig(
    filename='ytdownloader.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_FILE = Path.home() / '.ytdownloader' / 'config.json'
CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Constants
THUMBNAIL_SIZE = (120, 90)
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 700
QUEUE_POLL_INTERVAL = 100  # milliseconds
PAUSE_SLEEP_INTERVAL = 0.5  # seconds

def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load config: {e}")
    return {}

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        logger.error(f"Failed to save config: {e}")

def validate_url(url: str) -> bool:
    """Validate if URL is a valid video URL."""
    url = url.strip()
    return url.startswith(('http://', 'https://')) and len(url) > 10

def validate_proxy(proxy: str) -> bool:
    """Validate proxy format."""
    if not proxy.strip():
        return True  # Empty is valid (no proxy)
    # Basic proxy validation: should contain :// and have a host:port
    return '://' in proxy and ':' in proxy.split('://', 1)[1]

def validate_rate_limit(rate_limit: str) -> bool:
    """Validate rate limit format (e.g., 50K, 4.2M)."""
    if not rate_limit.strip():
        return True  # Empty is valid (no limit)
    import re
    return bool(re.match(r'^\d+(\.\d+)?[KMGT]?$', rate_limit.strip()))

def format_file_size(size_bytes: Optional[float]) -> str:
    """Format file size for display."""
    if size_bytes is None or size_bytes == 'N/A':
        return 'N/A'
    try:
        size_bytes = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"
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
        self.master = master
        master.title("YTDownloader - Advanced YouTube Video Downloader")
        master.geometry(f"{WINDOW_MIN_WIDTH}x{WINDOW_MIN_HEIGHT}")
        master.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

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

        self.ui_queue: queue.Queue = queue.Queue()
        self.master.after(QUEUE_POLL_INTERVAL, self.process_ui_queue)

        # --- UI Setup ---
        # Main frame
        self.frame = ttk.Frame(master, padding="20")
        self.frame.grid(row=0, column=0, sticky="nsew")
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)

        # Top frame for URL entry and theme switcher
        self.top_frame = ttk.Frame(self.frame)
        self.top_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 20))
        self.top_frame.grid_columnconfigure(1, weight=1)

        self.url_label = ttk.Label(self.top_frame, text="Video URL:")
        self.url_label.grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.url_entry = ttk.Entry(self.top_frame, width=60)
        self.url_entry.grid(row=0, column=1, sticky="ew")
        self.fetch_button = ttk.Button(self.top_frame, text="Fetch Info", command=self.fetch_info)
        self.fetch_button.grid(row=0, column=2, padx=5)
        self.theme_button = ttk.Button(self.top_frame, text="Toggle Theme", command=self.toggle_theme)
        self.theme_button.grid(row=0, column=3, padx=5)

        # Menu
        self.menubar = tk.Menu(master)
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.help_menu.add_command(label="About", command=self.show_about)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)
        master.config(menu=self.menubar)

        # Video Info Frame
        self.info_frame = ttk.LabelFrame(self.frame, text="Video Information", padding="10")
        self.info_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        self.thumbnail_label = ttk.Label(self.info_frame)
        self.thumbnail_label.grid(row=0, column=0, rowspan=3)
        self.title_label = ttk.Label(self.info_frame, text="Title: N/A")
        self.title_label.grid(row=0, column=1, sticky="w")
        self.duration_label = ttk.Label(self.info_frame, text="Duration: N/A")
        self.duration_label.grid(row=1, column=1, sticky="w")

        # Tabs for options
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="ew")

        self.video_tab = ttk.Frame(self.notebook)
        self.audio_tab = ttk.Frame(self.notebook)
        self.subtitle_tab = ttk.Frame(self.notebook)
        self.playlist_tab = ttk.Frame(self.notebook)
        self.chapters_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.downloads_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.video_tab, text="Video")
        self.notebook.add(self.audio_tab, text="Audio")
        self.notebook.add(self.subtitle_tab, text="Subtitles")
        self.notebook.add(self.playlist_tab, text="Playlist")
        self.notebook.add(self.chapters_tab, text="Chapters")
        self.notebook.add(self.settings_tab, text="Settings")
        self.notebook.add(self.downloads_tab, text="Downloads")

        # Video Tab
        self.video_format_label = ttk.Label(self.video_tab, text="Format:")
        self.video_format_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.video_format_var = tk.StringVar()
        self.video_format_menu = ttk.Combobox(self.video_tab, textvariable=self.video_format_var, state="readonly", width=40)
        self.video_format_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Audio Tab
        self.audio_format_label = ttk.Label(self.audio_tab, text="Format:")
        self.audio_format_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.audio_format_var = tk.StringVar()
        self.audio_format_menu = ttk.Combobox(self.audio_tab, textvariable=self.audio_format_var, state="readonly", width=40)
        self.audio_format_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Subtitle Tab
        self.subtitle_lang_label = ttk.Label(self.subtitle_tab, text="Language:")
        self.subtitle_lang_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.subtitle_lang_var = tk.StringVar()
        self.subtitle_lang_menu = ttk.Combobox(self.subtitle_tab, textvariable=self.subtitle_lang_var, state="readonly")
        self.subtitle_lang_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.subtitle_format_label = ttk.Label(self.subtitle_tab, text="Format:")
        self.subtitle_format_label.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.subtitle_format_var = tk.StringVar(value="srt")
        self.subtitle_format_menu = ttk.Combobox(self.subtitle_tab, textvariable=self.subtitle_format_var, values=["srt", "vtt", "ass"])
        self.subtitle_format_menu.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Playlist Tab
        self.playlist_var = tk.BooleanVar()
        self.playlist_check = ttk.Checkbutton(self.playlist_tab, text="Download Playlist", variable=self.playlist_var)
        self.playlist_check.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Chapters Tab
        self.chapters_var = tk.BooleanVar()
        self.chapters_check = ttk.Checkbutton(self.chapters_tab, text="Split Chapters", variable=self.chapters_var)
        self.chapters_check.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Settings Tab
        self.proxy_label = ttk.Label(self.settings_tab, text="Proxy:")
        self.proxy_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.proxy_entry = ttk.Entry(self.settings_tab, width=40)
        self.proxy_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.ratelimit_label = ttk.Label(self.settings_tab, text="Download Speed Limit (e.g., 50K, 4.2M):")
        self.ratelimit_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.ratelimit_entry = ttk.Entry(self.settings_tab, width=40)
        self.ratelimit_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Downloads Tab
        columns = ("URL", "Status", "Size", "Speed", "ETA")
        self.download_queue_tree = ttk.Treeview(self.downloads_tab, columns=columns, show="headings")
        self.download_queue_tree.heading("URL", text="URL")
        self.download_queue_tree.column("URL", width=300)
        self.download_queue_tree.heading("Status", text="Status")
        self.download_queue_tree.column("Status", width=100)
        self.download_queue_tree.heading("Size", text="Size")
        self.download_queue_tree.column("Size", width=100)
        self.download_queue_tree.heading("Speed", text="Speed")
        self.download_queue_tree.column("Speed", width=100)
        self.download_queue_tree.heading("ETA", text="ETA")
        self.download_queue_tree.column("ETA", width=100)
        self.download_queue_tree.pack(fill="both", expand=True)

        self.context_menu = tk.Menu(self.master, tearoff=0)
        self.context_menu.add_command(label="Cancel", command=self.cancel_download_item)
        self.context_menu.add_command(label="Remove", command=self.remove_from_queue)
        self.context_menu.add_command(label="Open File Location", command=self.open_file_location)
        self.download_queue_tree.bind("<Button-3>", self.show_context_menu)

        # Output Path
        self.path_label = ttk.Label(self.frame, text="Output Path:")
        self.path_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.path_entry = ttk.Entry(self.frame, width=50)
        self.path_entry.grid(row=4, column=1, padx=5, pady=5, columnspan=2, sticky="ew")
        self.browse_button = ttk.Button(self.frame, text="Browse...", command=self.browse_path)
        self.browse_button.grid(row=4, column=3, padx=5, pady=5)

        # Download Button, Clear Button, and Progress Bar
        self.download_button = ttk.Button(self.frame, text="Add to Queue", command=self.add_to_queue)
        self.download_button.grid(row=5, column=0, padx=5, pady=10)
        self.pause_button = ttk.Button(self.frame, text="Pause", command=self.toggle_pause_resume, state="disabled")
        self.pause_button.grid(row=5, column=1, padx=5, pady=10)
        self.cancel_button = ttk.Button(self.frame, text="Cancel", command=self.cancel_download, state="disabled")
        self.cancel_button.grid(row=5, column=2, padx=5, pady=10)
        self.clear_button = ttk.Button(self.frame, text="Clear", command=self.clear_ui)
        self.clear_button.grid(row=5, column=3, padx=5, pady=10)
        self.progress_bar = ttk.Progressbar(self.frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=6, column=0, columnspan=4, padx=5, pady=10, sticky="ew")
        self.status_label = ttk.Label(self.frame, text="")
        self.status_label.grid(row=7, column=0, columnspan=4, padx=5, pady=5)

        # Loading animation
        self.loading_animation_label = ttk.Label(self.info_frame, text="Fetching...")
        self.loading_animation_label.grid(row=1, column=1, sticky="w")
        self.loading_animation_label.grid_remove()

        # Set initial theme based on config
        theme = "dark" if self.dark_mode.get() else "light"
        sv_ttk.set_theme(theme)

        # Style configuration
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.map("TButton",
                  foreground=[('pressed', 'red'), ('active', 'blue')],
                  background=[('pressed', '!disabled', 'black'), ('active', 'white')])

    def toggle_theme(self) -> None:
        """Toggle between light and dark theme and persist preference."""
        sv_ttk.toggle_theme()
        self.dark_mode.set(not self.dark_mode.get())
        # Save theme preference
        self.config['dark_mode'] = self.dark_mode.get()
        save_config(self.config)
        logger.info(f"Theme changed to {'dark' if self.dark_mode.get() else 'light'}")

    def process_ui_queue(self):
        try:
            while True:
                task, kwargs = self.ui_queue.get_nowait()
                task(**kwargs)
        except queue.Empty:
            pass
        self.master.after(100, self.process_ui_queue)

    def clear_ui(self):
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
        self.status_label.config(text="")
        self.progress_bar['value'] = 0
        self.playlist_var.set(False)

    def fetch_info(self):
        """Fetch and display video information in a separate thread."""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a valid YouTube URL.")
            return

        if not validate_url(url):
            messagebox.showwarning("Invalid URL", "Please enter a valid URL starting with http:// or https://")
            return

        self.loading_animation_label.grid()
        self.fetch_button.config(state="disabled")
        self.status_label.config(text="Fetching video information...")

        def _fetch():
            try:
                info = get_video_info(url)
                if not info:
                    raise yt_dlp.utils.DownloadError("Failed to fetch video information.")

                title = info.get('title', 'N/A')
                duration = info.get('duration', 'N/A')

                self.ui_queue.put((self.title_label.config, {'text': f"Title: {title}"}))
                self.ui_queue.put((self.duration_label.config, {'text': f"Duration: {duration}"}))
                self.ui_queue.put((self.status_label.config, {'text': "Video info loaded successfully."}))

                self._video_streams = info.get('video_streams', [])
                self._audio_streams = info.get('audio_streams', [])

                if info.get('subtitles'):
                    self.ui_queue.put((self.subtitle_lang_menu.config, {'values': list(info['subtitles'].keys())}))
                    self.ui_queue.put((self.subtitle_lang_menu.set, {'value': ''}))

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

                # Load and display thumbnail
                if info.get('thumbnail'):
                    try:
                        response = requests.get(info['thumbnail'], timeout=5)
                        response.raise_for_status()
                        img_data = response.content
                        img = Image.open(BytesIO(img_data))
                        img.thumbnail(THUMBNAIL_SIZE)
                        photo = ImageTk.PhotoImage(img)
                        self.ui_queue.put((self.thumbnail_label.config, {'image': photo}))
                        self.thumbnail_label.image = photo
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

        self.fetch_thread = threading.Thread(target=_fetch, daemon=True)
        self.fetch_thread.start()

    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def progress_hook(self, d, item):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                downloaded_bytes = d['downloaded_bytes']
                percentage = (downloaded_bytes / total_bytes) * 100
                self.ui_queue.put((self.progress_bar.config, {'value': percentage}))

                item['size'] = f"{total_bytes / 1024 / 1024:.2f} MB"
                item['speed'] = d.get('speed', 'N/A')
                item['eta'] = d.get('eta', 'N/A')
                self.ui_queue.put((self.update_download_queue_list, {}))

        elif d['status'] == 'finished':
            self.ui_queue.put((self.progress_bar.config, {'value': 100}))
            self.ui_queue.put((self.status_label.config, {'text': "Download complete."}))
            item['status'] = 'Completed'
            self.ui_queue.put((self.update_download_queue_list, {}))

    def add_to_queue(self):
        """Add a download to the queue with validation."""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a URL.")
            return

        if not validate_url(url):
            messagebox.showwarning("Invalid URL", "Please enter a valid URL starting with http:// or https://")
            return

        video_format = self.video_format_var.get()
        if not video_format:
            messagebox.showwarning("Format Error", "Please fetch video info and select a video format.")
            return

        # Validate proxy format
        proxy = self.proxy_entry.get().strip()
        if proxy and not validate_proxy(proxy):
            messagebox.showerror("Invalid Proxy", "Invalid proxy format. Expected: protocol://host:port")
            return

        # Validate rate limit format
        rate_limit = self.ratelimit_entry.get().strip()
        if rate_limit and not validate_rate_limit(rate_limit):
            messagebox.showerror("Invalid Rate Limit", "Invalid rate limit format. Use: 50K, 4.2M, etc.")
            return

        # Validate output path
        output_path = self.path_entry.get().strip() or '.'
        if not Path(output_path).exists():
            messagebox.showerror("Invalid Path", f"Output directory does not exist: {output_path}")
            return

        audio_format = self.audio_format_var.get()
        subtitle_lang = self.subtitle_lang_var.get()
        subtitle_format = self.subtitle_format_var.get()
        playlist = self.playlist_var.get()
        split_chapters = self.chapters_var.get()

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
            "status": "Queued",
            "size": "N/A",
            "speed": "N/A",
            "eta": "N/A"
        }

        self.download_queue.append(download_item)
        logger.info(f"Added download to queue: {url}")
        self.update_download_queue_list()
        self.status_label.config(text=f"Added to queue. Queue size: {len(self.download_queue)}")

        if not self.is_downloading():
            self.process_download_queue()

    def update_download_queue_list(self):
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
        for item in self.download_queue:
            if item['status'] == 'Downloading':
                return True
        return False

    def process_download_queue(self):
        if not self.is_downloading():
            for item in self.download_queue:
                if item['status'] == 'Queued':
                    self.start_download_thread(item)
                    break

    def start_download_thread(self, item):
        item['status'] = 'Downloading'
        self.update_download_queue_list()
        self.download_button.config(state="disabled")
        self.pause_button.config(state="normal")
        self.cancel_button.config(state="normal")
        self.status_label.config(text=f"Downloading {item['url']}...")
        self.progress_bar['value'] = 0
        thread = threading.Thread(target=self.download, args=(item,))
        thread.start()

    def _extract_format_id(self, format_string: str) -> Optional[str]:
        """Safely extract format ID from format string."""
        if not format_string:
            return None
        # Format ID is at the end after ' - '
        parts = format_string.rsplit(' - ', 1)
        return parts[-1].strip() if parts else None

    def download(self, item: Dict[str, Any]) -> None:
        """Download video with proper error handling and cancellation."""
        self.cancel_token = CancelToken()
        try:
            # Wait if paused
            while self.is_paused:
                time.sleep(PAUSE_SLEEP_INTERVAL)
                if self.cancel_token.cancelled:
                    raise yt_dlp.utils.DownloadError("Download cancelled by user.")

            # Extract format IDs safely
            video_format_id = self._extract_format_id(item['video_format'])
            if not video_format_id:
                raise ValueError("Could not extract video format ID.")

            audio_format_id = self._extract_format_id(item['audio_format'])

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
                self.cancel_token
            )
            item['status'] = 'Completed'
            logger.info(f"Download completed: {item['url']}")

        except yt_dlp.utils.DownloadError as e:
            if "Download cancelled by user" in str(e):
                item['status'] = 'Cancelled'
                logger.info(f"Download cancelled: {item['url']}")
            else:
                item['status'] = 'Error'
                logger.error(f"Download error for {item['url']}: {e}")
                try:
                    self.handle_error(f"Download failed for {item['url']}", e)
                except RuntimeError:
                    pass
        except Exception as e:
            item['status'] = 'Error'
            logger.exception(f"Unexpected error during download of {item['url']}")
            try:
                self.handle_error(f"An unexpected error occurred", e)
            except RuntimeError:
                pass
        finally:
            self.cancel_token = None
            self.ui_queue.put((self.download_button.config, {'state': "normal"}))
            self.ui_queue.put((self.pause_button.config, {'state': "disabled"}))
            self.ui_queue.put((self.cancel_button.config, {'state': "disabled"}))
            self.ui_queue.put((self.update_download_queue_list, {}))
            self.ui_queue.put((self.process_download_queue, {}))
            if item['status'] == 'Completed':
                self.ui_queue.put((self.clear_ui, {}))

    def handle_error(self, message: str, error: Exception) -> None:
        """Handle and display errors."""
        logger.error(f"{message}: {type(error).__name__} - {error}")
        messagebox.showerror(
            "Error",
            f"{message}\n\n{type(error).__name__}: {error}\n\nCheck ytdownloader.log for details."
        )
        self.ui_queue.put((
            self.status_label.config,
            {'text': "An error occurred. See ytdownloader.log for details."}
        ))

    def cancel_download(self):
        if self.cancel_token:
            self.cancel_token.cancel()

    def toggle_pause_resume(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_button.config(text="Resume")
            self.status_label.config(text="Download paused.")
        else:
            self.pause_button.config(text="Pause")
            self.status_label.config(text="Resuming download...")

    def show_about(self):
        about_text = "YTDownloader\n\nVersion: 1.0\n\nA simple YouTube downloader built with Python and Tkinter."
        messagebox.showinfo("About", about_text)

    def show_context_menu(self, event):
        selection = self.download_queue_tree.identify_row(event.y)
        if selection:
            self.download_queue_tree.selection_set(selection)
            self.context_menu.post(event.x_root, event.y_root)

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
                return

            item_index = int(selection[0])
            if 0 <= item_index < len(self.download_queue):
                item = self.download_queue[item_index]
                if item['status'] == 'Downloading':
                    if messagebox.askyesno("Confirm", "Cancel the current download?"):
                        self.cancel_download()
                else:
                    item['status'] = 'Cancelled'
                    logger.info(f"Cancelled queued download: {item.get('url', 'Unknown')}")
                    self.update_download_queue_list()
            else:
                messagebox.showerror("Error", "Invalid queue item index.")
        except (IndexError, ValueError) as e:
            logger.error(f"Error cancelling download item: {e}")
            messagebox.showerror("Error", "Failed to cancel download item.")

    def open_file_location(self) -> None:
        """Open the output folder for the selected download."""
        try:
            selection = self.download_queue_tree.selection()
            if not selection:
                messagebox.showwarning("Selection Error", "Please select an item to open.")
                return

            item_index = int(selection[0])
            if 0 <= item_index < len(self.download_queue):
                item = self.download_queue[item_index]
                output_path = item.get('output_path', '.')

                if not Path(output_path).exists():
                    messagebox.showerror("Error", f"Output directory does not exist: {output_path}")
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
        except (IndexError, ValueError) as e:
            logger.error(f"Error opening file location: {e}")
            messagebox.showerror("Error", "Failed to open file location.")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.title("YTDownloader - Advanced YouTube Video Downloader")
        root.geometry(f"{WINDOW_MIN_WIDTH}x{WINDOW_MIN_HEIGHT}")
        root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # Try to set icon if available
        try:
            icon_path = Path(__file__).parent / "icon.ico"
            if icon_path.exists():
                root.iconbitmap(str(icon_path))
        except Exception:
            pass  # Icon not critical

        logger.info("YTDownloader started")
        app = YTDownloaderGUI(root)
        root.mainloop()
        logger.info("YTDownloader closed")
    except Exception as e:
        logger.exception("Fatal error in main")
        import tkinter.messagebox as mb
        mb.showerror("Fatal Error", f"An unexpected error occurred:\n{e}")
