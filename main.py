import tkinter as tk
from tkinter import ttk
from downloader import download_video
import threading

class YTDownloaderGUI:
    def __init__(self, master):
        self.master = master
        master.title("YTDownloader")

        self.url_label = ttk.Label(master, text="Video URL:")
        self.url_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.url_entry = ttk.Entry(master, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, columnspan=2)

        self.playlist_var = tk.BooleanVar()
        self.playlist_check = ttk.Checkbutton(master, text="Download Playlist", variable=self.playlist_var)
        self.playlist_check.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.format_label = ttk.Label(master, text="Format:")
        self.format_label.grid(row=1, column=1, padx=5, pady=5, sticky="e")

        self.format_var = tk.StringVar(value="best")
        self.format_menu = ttk.Combobox(master, textvariable=self.format_var, values=["best", "mp4", "webm", "mp3"])
        self.format_menu.grid(row=1, column=2, padx=5, pady=5, sticky="w")

        self.download_button = ttk.Button(master, text="Download", command=self.start_download_thread)
        self.download_button.grid(row=2, column=1, padx=5, pady=5)

        self.status_label = ttk.Label(master, text="")
        self.status_label.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

    def start_download_thread(self):
        self.download_button.config(state="disabled")
        self.status_label.config(text="Downloading...")
        thread = threading.Thread(target=self.download)
        thread.start()

    def download(self):
        url = self.url_entry.get()
        playlist = self.playlist_var.get()
        video_format = self.format_var.get()

        try:
            download_video(url, playlist, video_format)
            self.status_label.config(text="Download complete.")
        except Exception as e:
            self.status_label.config(text=f"An error occurred: {e}")
        finally:
            self.download_button.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = YTDownloaderGUI(root)
    root.mainloop()
