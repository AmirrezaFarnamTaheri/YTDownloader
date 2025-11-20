# Wiki

## Introduction

**YTDownloader** is a robust, feature-rich desktop application for downloading videos and audio from YouTube and other supported sites. Built with Python and Tkinter, it offers a modern, dark-themed user interface and leverages the powerful `yt-dlp` library for reliable downloads.

## Features

*   **Modern UI**: Clean, dark-themed interface using `sv_ttk`.
*   **Format Selection**: Choose specific video resolutions (1080p, 4K, etc.) and audio qualities.
*   **Audio Extraction**: Convert videos to high-quality audio (MP3, M4A, etc.).
*   **Batch Download**: Import a list of URLs from a text file to download en masse.
*   **Scheduler**: Schedule downloads to start at a specific time (e.g., during off-peak hours).
*   **Post-Processing**: Recode videos to MP4, MKV, AVI, etc., automatically after download.
*   **Subtitles**: Download subtitles in various languages and formats (SRT, VTT, ASS).
*   **Playlist Support**: Download entire playlists or channels.
*   **RSS Feed Monitoring**: Automatically check RSS feeds for new videos.
*   **Proxy & Rate Limit**: Configure proxy servers and limit download speeds.
*   **Browser Cookies**: Use cookies from your browser to bypass age restrictions and bot detection.
*   **Download History**: Keep track of your downloads with a built-in history manager.

## Usage Guide

### Basic Download
1.  Paste a YouTube URL into the input field (or use the "Paste" button).
2.  Click **Fetch Info** to load video details.
3.  Select your desired **Video Quality** and **Audio Format**.
4.  Choose a download location ("Save to").
5.  Click **Add to Queue**. The download will start automatically if the queue is processed.

### Batch Download
1.  Create a `.txt` file with one URL per line.
2.  Click the **Batch** button in the top bar.
3.  Select your text file. Valid URLs will be added to the queue.

### Scheduling
1.  Enter a URL and select formats as usual.
2.  Click the **Schedule** button in the bottom bar.
3.  Enter the start time in `HH:MM` format (24-hour clock).
4.  The item will sit in the queue with a "Scheduled" status until the time is reached.

### Post-Processing
1.  Go to the **Post-Processing** tab.
2.  Select a container format (e.g., `mp4`, `mkv`) from the "Recode Video to" dropdown.
3.  This ensures the final file is in your preferred format, even if YouTube provided a different one (like WebM).

## Troubleshooting

### "Sign in to confirm you’re not a bot"
*   Go to the **Settings** tab.
*   Under **Browser Cookies**, select the browser you use (e.g., Chrome, Firefox) where you are logged into YouTube.
*   Try fetching info again.

### FFmpeg Not Found
*   The app requires FFmpeg for merging video/audio and post-processing.
*   **Windows**: Download FFmpeg and add it to your System PATH, or place `ffmpeg.exe` in the app directory.
*   **Linux**: Install via `sudo apt install ffmpeg`.

### Download Error / Network Error
*   Check your internet connection.
*   If using a proxy, verify the settings in the **Settings** tab.
*   Update the application (check GitHub for releases) as `yt-dlp` needs frequent updates to stay ahead of YouTube changes.

## Developer Guide

### Setup
1.  Clone the repository.
2.  Install dependencies: `pip install -r requirements.txt`.
3.  Run the app: `python main.py`.

### Testing
Run unit tests with coverage:
```bash
pytest --cov=. --cov-report=term-missing tests/
```

### Building
To create a standalone executable:
```bash
pyinstaller --onefile --windowed --noconsole --name YTDownloader --icon=icon.ico main.py
```

## Roadmap
See [WHATS_NEXT.md](WHATS_NEXT.md) and [SUGGESTIONS.md](SUGGESTIONS.md) for future plans.
