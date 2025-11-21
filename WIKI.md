# StreamCatch Wiki

Welcome to the **StreamCatch** Wiki! StreamCatch is a modern, powerful, and soulful media downloader built with Python and Flet.

## Table of Contents
1. [Features](#features)
2. [Installation](#installation)
3. [Usage Guide](#usage-guide)
4. [Advanced Configuration](#advanced-configuration)
5. [Troubleshooting](#troubleshooting)

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

## Advanced Configuration

### Settings Tab
- **Proxy**: Set an HTTP/SOCKS proxy for downloads.
- **Rate Limit**: Limit download speed (e.g., `5M` for 5MB/s).
- **GPU Acceleration**: Enable CUDA or Vulkan for FFmpeg operations (requires hardware support).
- **Theme**: Toggle between Dark, Light, or System theme.

### Configuration File
Settings are stored in `~/.streamcatch/config.json`. You can manually edit this file if needed.

## Troubleshooting

**"FFmpeg not found"**
- Ensure FFmpeg is installed and added to your system PATH.
- On Windows, the installer script attempts to check this.

**"Download Error"**
- Check your internet connection.
- If it's a YouTube link, try updating `yt-dlp`: `pip install -U yt-dlp`.
- Try using "Force Generic" if the specific extractor fails.

**"Browser Cookies not working"**
- Ensure the selected browser is installed and you are logged in.
- Close the browser before starting the download to unlock the cookie database.

---
*Built with Soul by Jules.*
