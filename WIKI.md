# Wiki

## Introduction

**Lumina** (formerly YTDownloader) is a robust, feature-rich desktop application for downloading videos and audio from YouTube and other supported sites. Built with Python and Flet, it offers a modern, responsive user interface and leverages the powerful `yt-dlp` library for reliable downloads.

## Features

*   **Modern UI**: Clean, dark-themed interface using `Flet`.
*   **Format Selection**: Choose specific video resolutions (1080p, 4K, etc.) and audio qualities.
*   **Audio Extraction**: Convert videos to high-quality audio (MP3, M4A, etc.).
*   **Batch Download**: Import a list of URLs from a text file to download en masse.
*   **Scheduler**: Schedule downloads to start at a specific time (e.g., during off-peak hours).
*   **Cinema Mode**: A minimalist overlay for monitoring progress.
*   **Subtitles**: Download subtitles in various languages.
*   **Playlist Support**: Download entire playlists or channels.
*   **RSS Feed Monitoring**: Subscribe to RSS feeds to track channels.
*   **Proxy & Rate Limit**: Configure proxy servers and limit download speeds.
*   **Download History**: Keep track of your downloads with a built-in history manager and dashboard.

## Usage Guide

### Basic Download
1.  Paste a YouTube URL into the input field (or use the "Paste" button).
2.  Click **Fetch Info** to load video details.
3.  Select your desired **Video Quality** and **Audio Format** in the tabs.
4.  Click **Add to Queue**. The download will start automatically if the queue is processed.

### Batch Download
1.  Create a `.txt` file with one URL per line.
2.  Go to the **Advanced** tab.
3.  Click **Import Batch**.
4.  Select your text file. Valid URLs will be added to the queue.

### Scheduling
1.  Enter a URL and fetch info.
2.  Go to the **Advanced** tab.
3.  Click **Schedule**.
4.  Pick the start time.
5.  Click **Add to Queue**. The item will sit in the queue with a "Scheduled" status until the time is reached.

## Troubleshooting

### FFmpeg Not Found
*   The app requires FFmpeg for merging video/audio and post-processing.
*   **Windows**: Download FFmpeg and add it to your System PATH, or place `ffmpeg.exe` in the app directory.
*   **Linux**: Install via `sudo apt install ffmpeg`.

### Download Error / Network Error
*   Check your internet connection.
*   If using a proxy, verify the settings in the **Settings** tab.

## Developer Guide

### Setup
1.  Clone the repository.
2.  Install dependencies: `pip install -r requirements.txt`.
3.  Run the app: `python main.py`.

### Testing
Run unit tests:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Building
To create a standalone executable:
```bash
pyinstaller --onefile --windowed --noconsole --name Lumina --icon=assets/logo.ico main.py
```

## Roadmap
See [WHATS_NEXT.md](WHATS_NEXT.md) and [SUGGESTIONS.md](SUGGESTIONS.md) for future roadmap ideas.
