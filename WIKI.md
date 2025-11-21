# Wiki

## Introduction

**StreamCatch** (formerly YTDownloader/Lumina) is a robust, feature-rich desktop application for downloading media from the internet. Built with Python and Flet, it offers a modern, responsive user interface and leverages the powerful `yt-dlp` library alongside custom extractors for Telegram and generic files, emulating the capabilities of professional tools like Internet Download Manager (IDM).

## Features

*   **Modern UI**: Clean, dark-themed interface using `Flet` with a Navigation Rail and Dashboard.
*   **Universal Downloader**:
    *   **YouTube & Video Sites**: Supports thousands of sites via `yt-dlp` (YouTube, Twitch, etc.).
    *   **Social Media**: Dedicated support for **Twitter (X)**, **Instagram** (Reels/Posts), **TikTok**.
    *   **Telegram**: Scrape and download public files from Telegram channels (t.me links).
    *   **Generic Files**: Download any direct link (PDF, ISO, ZIP) robustly.
*   **Clipboard Monitor**: Automatically detects URLs copied to your system clipboard and prompts to download them.
*   **Format Selection**: Choose specific video resolutions (1080p, 4K, etc.) and audio qualities.
*   **Audio Extraction**: Convert videos to high-quality audio (MP3, M4A, etc.).
*   **Batch Download**: Import a list of URLs from a text file to download en masse.
*   **Scheduler**: Schedule downloads to start at a specific time.
*   **Cinema Mode**: A minimalist overlay for monitoring progress without distractions.
*   **Subtitles**: Download subtitles in various languages.
*   **Playlist Support**: Download entire playlists or channels with optional Regex filtering.
*   **RSS Feed Monitoring**: Subscribe to RSS feeds to track channels.
*   **Proxy & Rate Limit**: Configure proxy servers and limit download speeds.
*   **Download History & Dashboard**: Keep track of your downloads with a built-in history manager and view real-time statistics.
*   **Performance Tuning**: GPU acceleration (CUDA/Vulkan) and Aria2c external downloader support.

## Usage Guide

### Basic Download
1.  Paste a URL into the input field.
2.  Click **Fetch Info** (search icon) to load video details.
3.  Select your desired **Video Quality** and **Audio Format**.
4.  Optionally, select features like Playlist, SponsorBlock, or Time Range.
5.  Click **Add to Queue**. The download will start automatically if the queue is idle.

### Clipboard Monitor (Auto-Paste)
1.  Toggle the **Clipboard Monitor** switch in the top-right corner of the Download tab.
2.  Copy any supported URL (YouTube, Twitter, direct file link) in your browser.
3.  StreamCatch will automatically detect it, paste it into the URL field, and notify you via a SnackBar.

### Force Generic / Direct Download
If you have a link to a file (e.g., `http://example.com/file.zip`) or if automatic extraction fails:
1.  Paste the URL.
2.  Check the **Force Generic/Direct** checkbox.
3.  Click **Add to Queue**.
This bypasses metadata extraction and uses a direct stream download logic, similar to IDM.

### Batch Download
1.  Create a `.txt` file with one URL per line.
2.  Click **Batch Import**.
3.  Select your text file. Valid URLs will be added to the queue automatically.

### Scheduling
1.  Enter a URL and fetch info.
2.  Click **Schedule**.
3.  Pick the start time.
4.  Click **Add to Queue**. The item will sit in the queue with a "Scheduled" status until the time is reached.

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
pyinstaller --onefile --windowed --noconsole --name StreamCatch --icon=assets/logo.svg main.py
```

## Roadmap
See [WHATS_NEXT.md](WHATS_NEXT.md) and [SUGGESTIONS.md](SUGGESTIONS.md) for future roadmap ideas.
