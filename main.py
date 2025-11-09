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

class CancelToken:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def check(self, d):
        if self.cancelled:
            raise yt_dlp.utils.DownloadError("Download cancelled by user.")
        while self.is_paused:
            import time
            time.sleep(1)
            if self.cancelled:
                raise yt_dlp.utils.DownloadError("Download cancelled by user.")

# Configure logging
logging.basicConfig(filename='ytdownloader.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

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
        master.title("YTDownloader")

        # --- Application State ---
        self.dark_mode = tk.BooleanVar(value=True)

        self._video_streams = []
        self._audio_streams = []
        self.download_queue = []
        self.cancel_token = None
        self.is_paused = False

        self.ui_queue = queue.Queue()
        self.master.after(100, self.process_ui_queue)

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

        sv_ttk.set_theme("dark")

        # Style configuration
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.map("TButton",
                  foreground=[('pressed', 'red'), ('active', 'blue')],
                  background=[('pressed', '!disabled', 'black'), ('active', 'white')])

    def toggle_theme(self):
        """
        Toggles the theme between light and dark mode.
        """
        sv_ttk.toggle_theme()

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
        url = self.url_entry.get()
        if not url:
            self.status_label.config(text="Please enter a URL.")
            return

        self.loading_animation_label.grid()
        self.fetch_button.config(state="disabled")

        def _fetch():
            try:
                info = get_video_info(url)
                if not info:
                    raise yt_dlp.utils.DownloadError("Failed to fetch video information.")

                title = info.get('title', 'N/A')
                duration = info.get('duration', 'N/A')

                self.ui_queue.put((self.title_label.config, {'text': f"Title: {title}"}))
                self.ui_queue.put((self.duration_label.config, {'text': f"Duration: {duration}"}))

                self._video_streams = info.get('video_streams', [])
                self._audio_streams = info.get('audio_streams', [])

                if info.get('subtitles'):
                    self.ui_queue.put((self.subtitle_lang_menu.config, {'values': list(info['subtitles'].keys())}))
                    self.ui_queue.put((self.subtitle_lang_menu.set, {'value': ''}))

                video_formats = [
                    f"{s.get('resolution', 'N/A')}@{s.get('fps', 'N/A')}fps ({s.get('ext', 'N/A')}) - "
                    f"V:{s.get('vcodec', 'N/A')} A:{s.get('acodec', 'N/A')} "
                    f"({s.get('filesize', 'N/A') / 1024 / 1024:.2f} MB) - {s.get('format_id', 'N/A')}"
                    for s in self._video_streams
                ]
                self.ui_queue.put((self.video_format_menu.config, {'values': video_formats}))
                if video_formats:
                    self.ui_queue.put((self.video_format_menu.set, {'value': video_formats[0]}))

                audio_formats = [
                    f"{s.get('abr', 'N/A')}kbps ({s.get('ext', 'N/A')}) - A:{s.get('acodec', 'N/A')} "
                    f"({s.get('filesize', 'N/A') / 1024 / 1024:.2f} MB) - {s.get('format_id', 'N/A')}"
                    for s in self._audio_streams
                ]
                self.ui_queue.put((self.audio_format_menu.config, {'values': audio_formats}))
                if audio_formats:
                    self.ui_queue.put((self.audio_format_menu.set, {'value': audio_formats[0]}))

                if info.get('thumbnail'):
                    try:
                        response = requests.get(info['thumbnail'])
                        response.raise_for_status()
                        img_data = response.content
                        img = Image.open(BytesIO(img_data))
                        img.thumbnail((120, 90))
                        photo = ImageTk.PhotoImage(img)
                        self.ui_queue.put((self.thumbnail_label.config, {'image': photo}))
                        self.thumbnail_label.image = photo
                    except requests.exceptions.RequestException as e:
                        self.handle_error("Failed to fetch thumbnail.", e)
            except yt_dlp.utils.DownloadError as e:
                self.handle_error("Invalid URL or network error.", e)
            except Exception as e:
                self.handle_error("An unexpected error occurred.", e)
            finally:
                self.ui_queue.put((self.loading_animation_label.grid_remove, {}))
                self.ui_queue.put((self.fetch_button.config, {'state': "normal"}))

        threading.Thread(target=_fetch).start()

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
        url = self.url_entry.get()
        if not url:
            self.status_label.config(text="Please enter a URL.")
            return

        video_format = self.video_format_var.get()
        audio_format = self.audio_format_var.get()
        subtitle_lang = self.subtitle_lang_var.get()
        subtitle_format = self.subtitle_format_var.get()
        output_path = self.path_entry.get() or '.'
        playlist = self.playlist_var.get()
        split_chapters = self.chapters_var.get()
        proxy = self.proxy_entry.get()
        rate_limit = self.ratelimit_entry.get()

        download_item = {
            "url": url,
            "video_format": video_format,
            "audio_format": audio_format,
            "subtitle_lang": subtitle_lang,
            "subtitle_format": subtitle_format,
            "output_path": output_path,
            "playlist": playlist,
            "split_chapters": split_chapters,
            "proxy": proxy,
            "rate_limit": rate_limit,
            "status": "Queued"
        }

        self.download_queue.append(download_item)
        self.update_download_queue_list()

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

    def download(self, item):
        self.cancel_token = CancelToken()
        try:
            while self.is_paused:
                import time
                time.sleep(1)
                if self.cancel_token.cancelled:
                    raise yt_dlp.utils.DownloadError("Download cancelled by user.")

            video_format_id = item['video_format'].split(' - ')[-1]
            video_stream = next((s for s in self._video_streams if s['format_id'] == video_format_id), None)

            if video_stream and video_stream.get('acodec') != 'none':
                video_format = video_format_id
            else:
                audio_format_id = item['audio_format'].split(' - ')[-1]
                video_format = f"{video_format_id}+{audio_format_id}"

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
        except yt_dlp.utils.DownloadError as e:
            if "Download cancelled by user" in str(e):
                item['status'] = 'Cancelled'
            else:
                item['status'] = 'Error'
                self.handle_error(f"Download failed for {item['url']}.", e)
        except Exception as e:
            item['status'] = 'Error'
            self.handle_error(f"An unexpected error occurred during the download of {item['url']}.", e)
        finally:
            self.cancel_token = None
            self.ui_queue.put((self.download_button.config, {'state': "normal"}))
            self.ui_queue.put((self.pause_button.config, {'state': "disabled"}))
            self.ui_queue.put((self.cancel_button.config, {'state': "disabled"}))
            self.ui_queue.put((self.update_download_queue_list, {}))
            self.ui_queue.put((self.process_download_queue, {}))
            if item['status'] == 'Completed':
                self.ui_queue.put((self.clear_ui, {}))

    def handle_error(self, message, error):
        logging.error(f"{message}: {type(error).__name__} - {error}")
        messagebox.showerror("Error", f"{message}\n\n{type(error).__name__}: {error}")
        self.ui_queue.put((self.status_label.config, {'text': "An error occurred. See ytdownloader.log for details."}))

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

    def remove_from_queue(self):
        selected_item = self.download_queue_tree.selection()[0]
        item_index = int(selected_item)
        del self.download_queue[item_index]
        self.update_download_queue_list()

    def cancel_download_item(self):
        selected_item = self.download_queue_tree.selection()[0]
        item_index = int(selected_item)
        item = self.download_queue[item_index]
        if item['status'] == 'Downloading':
            self.cancel_download()
        else:
            item['status'] = 'Cancelled'
            self.update_download_queue_list()

    def open_file_location(self):
        selected_item = self.download_queue_tree.selection()[0]
        item_index = int(selected_item)
        item = self.download_queue[item_index]
        output_path = item['output_path']
        if sys.platform == "win32":
            os.startfile(output_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", output_path])
        else:
            subprocess.Popen(["xdg-open", output_path])

if __name__ == "__main__":
    root = tk.Tk()
    root.title("YTDownloader")
    root.geometry("800x600")
    # root.iconbitmap("path/to/icon.ico") # Placeholder for icon
    app = YTDownloaderGUI(root)
    root.mainloop()
