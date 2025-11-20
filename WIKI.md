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
    *   [Downloading Playlists](#downloading-playlists)
    *   [Audio Extraction](#audio-extraction)
    *   [Subtitles & Captions](#subtitles--captions)
    *   [Queue Management](#queue-management)
    *   [History & Retry](#history--retry)
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
*   Playlist and Channel downloading support.
*   Subtitle extraction (manual and auto-generated).
*   Browser cookies integration to bypass age restrictions.
*   Download queue with pause/resume/cancel capabilities.
*   Modern, responsive GUI with themes.

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
3.  Click **Fetch Info**. The app will retrieve metadata like title, duration, and available formats.
4.  **Select Format**: Choose your desired resolution (Video tab) or bitrate (Audio tab).
5.  **Select Path**: Choose where to save the file using the folder icon at the bottom.
6.  Click **Add to Queue**. The download will start automatically if the queue is not paused.

### <a name="interface-overview"></a> Interface Overview
*   **Hero Section**: URL input, Theme toggle (Moon/Sun icon), and Fetch button.
*   **Left Panel**:
    *   **Preview**: Shows video thumbnail and details.
    *   **Tabs**: Video, Audio, Advanced, Settings.
*   **Right Panel**:
    *   **Queue**: List of pending, active, and completed downloads.
    *   **Controls**: Clear All, Move Up/Down (coming soon).
*   **Bottom Bar**: Path selection, Add to Queue, Pause/Resume, Cancel.

### <a name="downloading-playlists"></a> Downloading Playlists
1.  Paste a Playlist URL.
2.  Go to the **Advanced** tab.
3.  Check **Download Playlist**.
4.  When you click **Add to Queue**, all videos in the playlist will be added sequentially.

### <a name="audio-extraction"></a> Audio Extraction
1.  After fetching info, switch to the **Audio** tab.
2.  Select a format (e.g., `128kbps (M4A)` or `192kbps (MP3)`).
3.  Click **Add to Queue**. The app will download the video and convert/extract the audio track.
    *   *Note: FFmpeg is required for high-quality audio conversion (e.g., to MP3).*

### <a name="subtitles--captions"></a> Subtitles & Captions
1.  Go to the **Advanced** tab.
2.  **Subtitle Language**: Select your preferred language from the dropdown.
    *   Note: Languages marked `(Auto)` are auto-generated by YouTube.
3.  **Format**: Choose `.srt` (most compatible), `.vtt`, or `.ass`.
4.  The subtitle file will be saved alongside the video.

---

## <a name="advanced-features"></a> 4. Advanced Features

### <a name="cookies--authentication"></a> Cookies & Authentication
If a video is age-restricted or requires a premium account:
1.  Go to the **Settings** tab.
2.  **Browser Cookies**: Select the browser where you are logged into YouTube (e.g., Chrome, Firefox).
3.  **Profile**: (Optional) Specify a browser profile name if you use multiple profiles.
4.  The app will use `yt-dlp`'s cookie extraction to authenticate the request.

### <a name="proxy-configuration"></a> Proxy Configuration
For users in restricted network environments:
1.  Go to **Settings**.
2.  Enter the proxy URL in the format: `http://user:pass@host:port` or `socks5://host:port`.
3.  Downloads will be routed through this proxy.

### <a name="rate-limiting"></a> Rate Limiting
To prevent the downloader from consuming all bandwidth:
1.  Go to **Settings**.
2.  Enter a limit in **Rate Limit** (e.g., `5M` for 5MB/s, `500K` for 500KB/s).

### <a name="ffmpeg-integration"></a> FFmpeg Integration
YTDownloader automatically detects FFmpeg if it is in your system PATH or placed in the application directory.
*   **Required for:** Merging best video+audio streams (1080p+), converting to MP3, and embedding thumbnails.
*   **Indicator:** The UI will show an FFmpeg icon (green check) if detected.

### <a name="time-range-downloading"></a> Time Range Downloading
*Use this to download only a specific clip of a video.*
1.  Go to **Advanced**.
2.  **Start Time**: Enter start timestamp (e.g., `00:01:30`).
3.  **End Time**: Enter end timestamp (e.g., `00:02:00`).
4.  This uses the `--download-sections` feature of yt-dlp.

---

## <a name="troubleshooting"></a> 5. Troubleshooting

| Issue | Possible Cause | Solution |
| :--- | :--- | :--- |
| **Download Fails Immediately** | Invalid URL or Network issue | Check internet connection and URL validity. |
| **"Sign in to confirm..."** | Age restriction | Enable **Browser Cookies** in Settings. |
| **Audio Missing/Low Quality** | FFmpeg missing | Install FFmpeg or ensure it's in the PATH. |
| **App Crashes on Launch** | Missing dependencies | Run `pip install -r requirements.txt`. |
| **Slow Download Speed** | ISP throttling or YouTube limits | Try a different network or restart the app. |

**Logs:**
Application logs are saved to `ytdownloader.log` in the installation directory. Check this file for detailed error messages.

---

## <a name="developer-guide"></a> 6. Developer Guide

### <a name="architecture-overview"></a> Architecture Overview
The application follows a modular structure:

*   **`main.py`**: The Controller and View. Initializes the Tkinter `root`, handles the event loop, and manages UI widgets. It uses `queue.Queue` to safely communicate between background download threads and the main GUI thread.
*   **`downloader.py`**: The Model. Wraps `yt-dlp` logic. It exposes `get_video_info` for metadata and `download_video` for the actual process. It utilizes callbacks for progress reporting.
*   **`config_manager.py`**: Singleton-like class for loading/saving `config.json`.
*   **`ui_utils.py`**: specific UI helpers, constants, and validators.
*   **`history_manager.py`**: (New) Manages SQLite database for download history.

### <a name="environment-setup"></a> Environment Setup
We recommend using **VS Code** or **PyCharm**.
1.  Ensure `Python 3.10+` is installed.
2.  Install development dependencies (pytest, pylint):
    ```bash
    pip install pytest pylint yt-dlp sv-ttk
    ```

### <a name="running-tests"></a> Running Tests
The project uses `unittest`.
*   **Run all tests:**
    ```bash
    python -m unittest discover tests
    ```
*   **Run specific test file:**
    ```bash
    python -m unittest tests/test_downloader.py
    ```
*   **Headless GUI Testing:**
    The project includes `headless_tk.py` to mock Tkinter for CI environments.
    On Linux, use `xvfb-run`.

### <a name="building-executables"></a> Building Executables
We use **PyInstaller**.
1.  Install PyInstaller: `pip install pyinstaller`
2.  Run the build command:
    ```bash
    pyinstaller --noconsole --onefile --name="YTDownloader" --icon="icon.ico" --add-data "sv_ttk;sv_ttk" --hidden-import="PIL._tkinter_finder" main.py
    ```
    *Note: Check `ytdownloader.spec` for the precise configuration.*

### <a name="contribution-guidelines"></a> Contribution Guidelines
1.  **Fork** the repository.
2.  Create a **feature branch** (`git checkout -b feature/amazing-feature`).
3.  Commit your changes.
4.  **Verify** with tests.
5.  Push to the branch and open a **Pull Request**.
