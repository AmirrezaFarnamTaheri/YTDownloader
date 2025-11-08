import tkinter as tk
from tkinter import ttk, filedialog
from ttkthemes import ThemedTk
from downloader import download_video, get_video_info
import threading
from PIL import Image, ImageTk
import requests
from io import BytesIO
import queue

class YTDownloaderGUI:
    def __init__(self, master):
        self.master = master
        master.title("YTDownloader")
        master.set_theme("arc")

        self.ui_queue = queue.Queue()
        self.master.after(100, self.process_ui_queue)

        # Main frame
        self.frame = ttk.Frame(master, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew")

        # URL Entry
        self.url_label = ttk.Label(self.frame, text="Video URL:")
        self.url_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.url_entry = ttk.Entry(self.frame, width=60)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, columnspan=2, sticky="ew")
        self.fetch_button = ttk.Button(self.frame, text="Fetch Info", command=self.fetch_info)
        self.fetch_button.grid(row=0, column=3, padx=5, pady=5)

        # Video Info Frame
        self.info_frame = ttk.LabelFrame(self.frame, text="Video Information", padding="10")
        self.info_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        self.thumbnail_label = ttk.Label(self.info_frame)
        self.thumbnail_label.grid(row=0, column=0, rowspan=3)
        self.title_label = ttk.Label(self.info_frame, text="Title: N/A")
        self.title_label.grid(row=0, column=1, sticky="w")
        self.duration_label = ttk.Label(self.info_frame, text="Duration: N/A")
        self.duration_label.grid(row=1, column=1, sticky="w")

        # Options
        self.playlist_var = tk.BooleanVar()
        self.playlist_check = ttk.Checkbutton(self.frame, text="Download Playlist", variable=self.playlist_var)
        self.playlist_check.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.format_label = ttk.Label(self.frame, text="Format:")
        self.format_label.grid(row=2, column=1, padx=5, pady=5, sticky="e")
        self.format_var = tk.StringVar(value="best")
        self.format_menu = ttk.Combobox(self.frame, textvariable=self.format_var, values=["best", "mp4", "webm", "mp3"])
        self.format_menu.grid(row=2, column=2, padx=5, pady=5, sticky="w")

        # Subtitles
        self.subtitle_lang_label = ttk.Label(self.frame, text="Subtitle Language:")
        self.subtitle_lang_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.subtitle_lang_var = tk.StringVar()
        self.subtitle_lang_menu = ttk.Combobox(self.frame, textvariable=self.subtitle_lang_var, state="readonly")
        self.subtitle_lang_menu.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        self.subtitle_format_label = ttk.Label(self.frame, text="Subtitle Format:")
        self.subtitle_format_label.grid(row=3, column=2, padx=5, pady=5, sticky="e")
        self.subtitle_format_var = tk.StringVar(value="srt")
        self.subtitle_format_menu = ttk.Combobox(self.frame, textvariable=self.subtitle_format_var, values=["srt", "vtt", "ass"])
        self.subtitle_format_menu.grid(row=3, column=3, padx=5, pady=5, sticky="w")

        # Output Path
        self.path_label = ttk.Label(self.frame, text="Output Path:")
        self.path_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.path_entry = ttk.Entry(self.frame, width=50)
        self.path_entry.grid(row=4, column=1, padx=5, pady=5, columnspan=2, sticky="ew")
        self.browse_button = ttk.Button(self.frame, text="Browse...", command=self.browse_path)
        self.browse_button.grid(row=4, column=3, padx=5, pady=5)

        # Download Button and Progress Bar
        self.download_button = ttk.Button(self.frame, text="Download", command=self.start_download_thread)
        self.download_button.grid(row=5, column=1, padx=5, pady=5)
        self.progress_bar = ttk.Progressbar(self.frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=6, column=0, columnspan=4, padx=5, pady=10, sticky="ew")
        self.status_label = ttk.Label(self.frame, text="")
        self.status_label.grid(row=7, column=0, columnspan=4, padx=5, pady=5)

    def process_ui_queue(self):
        try:
            while True:
                task, kwargs = self.ui_queue.get_nowait()
                task(**kwargs)
        except queue.Empty:
            pass
        self.master.after(100, self.process_ui_queue)

    def fetch_info(self):
        url = self.url_entry.get()
        if not url:
            self.status_label.config(text="Please enter a URL.")
            return

        def _fetch():
            try:
                info = get_video_info(url)
                self.ui_queue.put((self.title_label.config, {'text': f"Title: {info['title']}"}))
                self.ui_queue.put((self.duration_label.config, {'text': f"Duration: {info['duration']}"}))

                if info['subtitles']:
                    self.ui_queue.put((self.subtitle_lang_menu.config, {'values': list(info['subtitles'].keys())}))
                    self.ui_queue.put((self.subtitle_lang_menu.set, {'value': ''}))

                if info['thumbnail']:
                    response = requests.get(info['thumbnail'])
                    img_data = response.content
                    img = Image.open(BytesIO(img_data))
                    img.thumbnail((120, 90))
                    photo = ImageTk.PhotoImage(img)
                    self.ui_queue.put((self.thumbnail_label.config, {'image': photo}))
                    self.thumbnail_label.image = photo
            except Exception as e:
                self.ui_queue.put((self.status_label.config, {'text': f"Error fetching info: {e}"}))

        threading.Thread(target=_fetch).start()

    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                downloaded_bytes = d['downloaded_bytes']
                percentage = (downloaded_bytes / total_bytes) * 100
                self.ui_queue.put((self.progress_bar.config, {'value': percentage}))
        elif d['status'] == 'finished':
            self.ui_queue.put((self.progress_bar.config, {'value': 100}))
            self.ui_queue.put((self.status_label.config, {'text': "Download complete."}))

    def start_download_thread(self):
        self.download_button.config(state="disabled")
        self.status_label.config(text="Downloading...")
        self.progress_bar['value'] = 0
        thread = threading.Thread(target=self.download)
        thread.start()

    def download(self):
        url = self.url_entry.get()
        playlist = self.playlist_var.get()
        video_format = self.format_var.get()
        output_path = self.path_entry.get() or '.'
        subtitle_lang = self.subtitle_lang_var.get()
        subtitle_format = self.subtitle_format_var.get()

        try:
            download_video(url, self.progress_hook, playlist, video_format, output_path, subtitle_lang, subtitle_format)
        except Exception as e:
            self.ui_queue.put((self.status_label.config, {'text': f"An error occurred: {e}"}))
        finally:
            self.ui_queue.put((self.download_button.config, {'state': "normal"}))

if __name__ == "__main__":
    root = ThemedTk(theme="arc")
    app = YTDownloaderGUI(root)
    root.mainloop()
