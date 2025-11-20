# YTDownloader Wiki

Welcome to the comprehensive documentation for **YTDownloader**, an advanced, open-source desktop application for downloading videos and audio from YouTube and other supported platforms. This wiki covers everything from installation to advanced developer guides.

---

## 📚 Table of Contents

1.  [Introduction](#introduction)
2.  [Installation Guide](#installation-guide)
    *   [Windows](#windows)
    *   [Linux](#linux)
    *   [macOS](#macos)
    *   [Running from Source](#running-from-source)
3.  [User Guide](#user-guide)
    *   [Basic Usage](#basic-usage)
    *   [Interface Overview](#interface-overview)
    *   [RSS Feeds](#rss-feeds)
    *   [Localization](#localization)
    *   [Downloading Playlists](#downloading-playlists)
    *   [Audio Extraction](#audio-extraction)
    *   [Subtitles & Captions](#subtitles--captions)
    *   [Queue Management](#queue-management)
    *   [History & Playback](#history--playback)
4.  [Advanced Features](#advanced-features)
    *   [Cookies & Authentication](#cookies--authentication)
    *   [Proxy Configuration](#proxy-configuration)
    *   [Rate Limiting](#rate-limiting)
    *   [FFmpeg Integration](#ffmpeg-integration)
    *   [Time Range Downloading](#time-range-downloading)
5.  [Troubleshooting](#troubleshooting)
6.  [Developer Guide](#developer-guide)
    *   [Architecture Overview](#architecture-overview)
    *   [Environment Setup](#environment-setup)
    *   [Running Tests](#running-tests)
    *   [Building Executables](#building-executables)
    *   [Contribution Guidelines](#contribution-guidelines)

---

## <a name="introduction"></a> 1. Introduction

YTDownloader is built with **Python** and **Tkinter**, utilizing the powerful `yt-dlp` library as its core downloading engine. It features a modern UI styled with `sv-ttk`, support for dark mode, and a robust multi-threaded architecture to ensure the interface remains responsive during downloads.

**Key Features:**
*   Download Video (up to 4K/8K) and Audio (MP3, M4A, WAV, etc.).
*   **RSS Feed Integration** for channel updates.
*   **Multilingual Support** (English, Spanish, Farsi).
*   Playlist and Channel downloading support.
*   Subtitle extraction (manual and auto-generated).
*   Browser cookies integration to bypass age restrictions.
*   Download queue with pause/resume/cancel capabilities.
*   Integrated file player opener.

---

## <a name="installation-guide"></a> 2. Installation Guide

### <a name="windows"></a> Windows

**Method 1: One-Click Installer (Recommended)**
1.  Download the latest source code zip or clone the repository.
2.  Double-click `install-and-run.bat`.
3.  This script will automatically:
    *   Check for Python.
    *   Create a virtual environment.
    *   Install dependencies.
    *   Launch the application.
    *   Create a desktop shortcut.

**Method 2: Standalone Executable**
1.  Go to the **Releases** page (if available) and download `YTDownloader.exe`.
2.  Run the executable directly. No Python installation required.

### <a name="linux"></a> Linux

**Prerequisites:**
*   Python 3.8 or higher
*   `python3-venv`, `python3-tk`, and `ffmpeg` (optional but recommended).

**Installation:**
1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/YTDownloader.git
    cd YTDownloader
    ```
2.  Run the setup script:
    ```bash
    chmod +x install-and-run.sh
    ./install-and-run.sh
    ```

### <a name="macos"></a> macOS

**Prerequisites:**
*   Python 3.8+ (install via Homebrew: `brew install python`)
*   `ffmpeg` (recommended: `brew install ffmpeg`)

**Installation:**
1.  Clone the repository.
2.  Run:
    ```bash
    chmod +x install-and-run.sh
    ./install-and-run.sh
    ```

### <a name="running-from-source"></a> Running from Source

If you prefer to manage the environment yourself:

1.  **Clone & Enter Directory:**
    ```bash
    git clone <repo_url>
    cd YTDownloader
    ```
2.  **Create Virtual Environment:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run Application:**
    ```bash
    python main.py
    ```

---

## <a name="user-guide"></a> 3. User Guide

### <a name="basic-usage"></a> Basic Usage
1.  **Copy a URL** from YouTube (video, playlist, or channel).
2.  **Paste** it into the top input field (or use `Ctrl+V`).
3.  Click **Fetch Info**. The app will retrieve metadata.
4.  **Select Format**: Choose your desired resolution or audio format.
5.  **Select Path**: Choose where to save the file.
6.  Click **Add to Queue**.

### <a name="interface-overview"></a> Interface Overview
*   **Hero Section**: URL input, Theme toggle, and Fetch button.
*   **Tabs**: Video, Audio, Advanced, RSS, Settings.
*   **Queue**: List of pending/active downloads.
*   **History**: Log of completed downloads with playback options.

### <a name="rss-feeds"></a> RSS Feeds
Use the **RSS** tab to subscribe to YouTube channels.
1.  Paste a Channel RSS URL (often `https://www.youtube.com/feeds/videos.xml?channel_id=...`).
2.  Click **Add**.
3.  Click **Check Now** to retrieve the latest video from all subscribed feeds.

### <a name="localization"></a> Localization
Go to **Settings** and select your language (English, Spanish, Farsi). Restart the application to apply changes.

### <a name="history--playback"></a> History & Playback
In the **History** tab, you can view past downloads.
*   **Retry**: Re-load the URL into the main downloader.
*   **Play**: Open the downloaded file in your default media player (double-click or use the Play button).

### <a name="downloading-playlists"></a> Downloading Playlists
1.  Paste a Playlist URL.
2.  Go to the **Advanced** tab.
3.  Check **Download Playlist**.
4.  Click **Add to Queue**.

### <a name="audio-extraction"></a> Audio Extraction
1.  After fetching info, switch to the **Audio** tab.
2.  Select a format (e.g., `128kbps (M4A)`).
3.  Click **Add to Queue**.

### <a name="subtitles--captions"></a> Subtitles & Captions
1.  Go to the **Advanced** tab.
2.  **Subtitle Language**: Select your preferred language.
3.  **Format**: Choose `.srt`, `.vtt`, or `.ass`.

---

## <a name="advanced-features"></a> 4. Advanced Features

### <a name="cookies--authentication"></a> Cookies & Authentication
If a video is age-restricted:
1.  Go to the **Settings** tab.
2.  **Browser Cookies**: Select the browser where you are logged into YouTube.
3.  **Profile**: (Optional) Specify profile name.

### <a name="proxy-configuration"></a> Proxy Configuration
1.  Go to **Settings**.
2.  Enter the proxy URL in the format: `http://user:pass@host:port` or `socks5://host:port`.

### <a name="rate-limiting"></a> Rate Limiting
1.  Go to **Settings**.
2.  Enter a limit in **Rate Limit** (e.g., `5M` for 5MB/s).

### <a name="ffmpeg-integration"></a> FFmpeg Integration
YTDownloader automatically detects FFmpeg if it is in your system PATH. Required for high-quality merges and conversions.

### <a name="time-range-downloading"></a> Time Range Downloading
*Use this to download only a specific clip.*
1.  Go to **Advanced**.
2.  **Start/End Time**: Enter timestamps (e.g., `00:01:30`).

---

## <a name="troubleshooting"></a> 5. Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **Download Fails** | Check internet and URL. |
| **"Sign in..."** | Enable **Browser Cookies** in Settings. |
| **Audio Missing** | Install FFmpeg. |
| **Crash on Launch** | Run `pip install -r requirements.txt`. |

---

## <a name="developer-guide"></a> 6. Developer Guide

### <a name="architecture-overview"></a> Architecture Overview
*   **`main.py`**: Controller and View.
*   **`downloader.py`**: Model (wraps `yt-dlp`).
*   **`rss_manager.py`**: Handles RSS feed parsing.
*   **`localization_manager.py`**: Manages i18n.
*   **`history_manager.py`**: SQLite database management.

### <a name="environment-setup"></a> Environment Setup
1.  `Python 3.10+` required.
2.  `pip install -r requirements.txt`

### <a name="running-tests"></a> Running Tests
```bash
python -m unittest discover tests
```

### <a name="building-executables"></a> Building Executables
```bash
pyinstaller ytdownloader.spec
```
