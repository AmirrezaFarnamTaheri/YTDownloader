# StreamCatch Wiki

Welcome to the **StreamCatch** Wiki! StreamCatch is a modern, powerful, and soulful media downloader built with Python and Flet. This documentation covers the architecture, features, and advanced usage of the StreamCatch media downloader.

## Table of Contents
1. [Features](#features)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Usage Guide](#usage-guide)
5. [Advanced Configuration & Features](#advanced-configuration--features)
6. [Troubleshooting](#troubleshooting)

---

## Features

- **Universal Downloader**: Support for YouTube, Telegram, Twitter, Instagram, and generic file links.
- **Modern UI**: A sleek, "soulful" dark-themed interface using Material Design 3.
- **Queue Management**: Batch processing, reordering, retry logic, and scheduling.
- **Smart Features**:
    - **Clipboard Monitor**: Auto-detects links copied to your clipboard.
    - **SponsorBlock**: Skip non-content segments in YouTube videos.
    - **Browser Cookies**: Bypass age-gating or login requirements by using cookies from your browser.
- **Performance**:
    - **Aria2c Integration**: Acceleration for multi-connection downloads.
    - **GPU Acceleration**: Hardware-accelerated post-processing (FFmpeg).
- **RSS Integration**: Follow your favorite channels and download latest videos.
- **Cloud Upload**: (Experimental) Upload finished downloads to Google Drive.

---

## Architecture

StreamCatch uses a modular architecture to ensure robustness and maintainability.

### Frontend
- **Framework**: Flet (based on Flutter).
- **Design System**: Material Design 3.
- **Platform**: Windows, macOS, Linux, Web, iOS, Android.
- **State Management**: `AppState` singleton with observable properties.

### Backend
- **Downloader Engine**: `yt-dlp` for video extraction, `requests` for generic file downloads.
- **Queue Management**: `QueueManager` provides atomic, thread-safe operations for managing concurrent downloads.
- **Storage**: SQLite via `HistoryManager` for persistent history; JSON for configuration.

### Pipeline
1.  **Input**: URL from user or Clipboard Monitor.
2.  **Validation**: `ui_utils.validate_url`.
3.  **Info Extraction**: `downloader.get_video_info` (tries `yt-dlp` -> `TelegramExtractor` -> `GenericExtractor`).
4.  **Queuing**: Item added to `QueueManager`.
5.  **Processing**: Background thread claims item via `claim_next_downloadable()`.
6.  **Downloading**: `downloader.download_video` executes the download with progress hooks.
7.  **Post-Processing**: FFmpeg (conversion, metadata, thumbnail).
8.  **Completion**: History updated, notification sent.

---

## Installation

### Windows
1. Download the latest release or clone the repo.
2. Run `install-and-run.bat` (Command Prompt) or `install-and-run.ps1` (PowerShell).
   - This script sets up a virtual environment, installs dependencies, and launches the app.

### Linux / macOS
1. Ensure `python3` and `ffmpeg` are installed.
2. Run `./install-and-run.sh`.

### Manual Setup
```bash
pip install -r requirements.txt
python main.py
```

---

## Usage Guide

### Downloading a Video
1. **Paste URL**: Copy a link and paste it into the URL field in the **Download** tab.
2. **Fetch Info**: Click the Search icon to retrieve metadata (title, formats).
3. **Select Options**:
   - Choose **Video Quality** and **Audio Format**.
   - Enable **Playlist** if the link is a playlist.
   - Select **Browser Cookies** if the video is age-restricted.
4. **Add to Queue**: Click "Add to Queue". The download will start automatically.

### Managing the Queue
- Navigate to the **Queue** tab.
- **Reorder**: Use Up/Down arrows to prioritize downloads.
- **Cancel/Retry**: Cancel running downloads or retry failed ones.
- **Clear**: Remove finished items to clean up the view.

### RSS Feeds
1. Go to the **RSS** tab.
2. Paste a channel URL (e.g., `https://www.youtube.com/feeds/videos.xml?channel_id=...`).
3. Click **Add**.
4. Switch to the **Latest Items** tab to see recent videos and copy their links.

---

## Advanced Configuration & Features

### Core Components

#### Downloader Module (`downloader.py`)
The heart of the application. It wraps `yt-dlp` but adds a robust layer of error handling and fallback mechanisms.
- **Robustness**: If `yt-dlp` fails to identify a URL (e.g., a direct file link served with `content-disposition`), it falls back to `GenericExtractor`.
- **Telegram**: A custom `TelegramExtractor` scrapes public Telegram channels for video/image content.

#### Queue Manager (`queue_manager.py`)
Handles the download queue.
- **Thread Safety**: All operations are locked.
- **Atomic Claiming**: The `claim_next_downloadable()` method prevents race conditions where multiple worker threads might try to download the same file.

#### Generic Downloader (`generic_downloader.py`)
A specialized module for non-video sites.
- **Streaming**: Downloads large files in chunks to keep memory usage low.
- **Resumability**: (Future plan) Can be extended to support `Range` headers.

### Settings
- **Proxy**: Set an HTTP/SOCKS proxy for downloads.
- **Rate Limit**: Limit download speed (e.g., `5M` for 5MB/s).
- **GPU Acceleration**: Enable CUDA or Vulkan for FFmpeg operations (requires hardware support).
- **Theme**: Toggle between Dark, Light, or System theme.

### Configuration File
Settings are stored in `~/.streamcatch/config.json`. You can manually edit this file if needed.

### Special Modes
- **Force Generic Mode**: Bypasses extraction logic and treats the URL as a direct download source (useful for direct CDN links).
- **Time Range Downloading**: Uses `yt-dlp`'s `download_ranges` to download only a portion of a video (Format: `HH:MM:SS`).

---

## Troubleshooting

### "FFmpeg not found"
- Ensure FFmpeg is installed and added to your system PATH.
- On Windows, the installer script attempts to check this.

### "Download Error"
- Check your internet connection.
- Verify the URL works in a browser.
- If it's a YouTube link, try updating `yt-dlp`: `pip install -U yt-dlp`.
- Try "Force Generic" if it's a direct file link.

### "Browser Cookies not working"
- Ensure the selected browser is installed and you are logged in.
- Close the browser before starting the download to unlock the cookie database.

### Visual Glitches
If the UI looks incorrect, ensure you are not using a custom scaling factor that interferes with Flet/Flutter rendering.

---
*Built with Soul by Jules.*
