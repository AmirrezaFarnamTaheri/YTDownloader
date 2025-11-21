# StreamCatch - Ultimate Media Downloader

![License](https://img.shields.io/badge/license-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Status](https://img.shields.io/badge/status-stable-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

**StreamCatch** is a professional-grade, cross-platform media downloader designed for robustness, speed, and aesthetics. Built with Python and Flet, it offers a modern Material Design 3 interface with advanced features for power users, emulating the best features of IDM (Internet Download Manager).

## 👤 Credits

*   **Author**: Amirreza "Farnam" Taheri
*   **Contact**: taherifarnam@gmail.com
*   **Github**: [AmirrezaFarnamTaheri](https://github.com/AmirrezaFarnamTaheri)

## 🌟 Key Features

### 🎨 Modern & Immersive UI
- **Navigation Rail**: Clean sidebar navigation for quick access to Queues, History, and Settings.
- **Cinema Mode**: An immersive, distraction-free overlay for monitoring active downloads.
- **Dashboard**: Real-time analytics and download statistics (Total Downloads, etc.).
- **Card-Based Design**: Beautiful, responsive cards for download items with progress visualization.
- **Platform Icons**: Quick indicators for YouTube, Telegram, Twitter, Instagram, and Generic Files.

### ⚡ Performance & Robustness
- **Multi-threaded Queue**: A fully thread-safe `QueueManager` with atomic task claiming ensures stability and prevents race conditions.
- **Aria2c Integration**: Accelerate downloads with multi-connection support (up to 16x speeds).
- **GPU Acceleration**: Hardware-accelerated encoding/decoding (NVENC/VAAPI/QSV) via FFmpeg.
- **Smart Resume**: Robust error handling and resume capabilities for interrupted downloads.
- **IDM-Like Logic**: Optimized for speed and reliability.

### 🛠 Advanced Tools
- **Universal Site Support**:
  - **YouTube**: 4K Video, Audio, Playlists, Channels.
  - **Social Media**: **Twitter (X)**, **Instagram** (Reels/Posts), Twitch, TikTok.
  - **Telegram**: Download videos and images from public channels.
  - **Generic Files**: Direct download support for any file type (PDF, ZIP, ISO, etc.) with **Force Generic** mode.
- **Clipboard Monitor**: Automatically detects URLs copied to the clipboard and prepares them for download.
- **Time Range**: Download specific clips (Start/End time) without downloading the full video.
- **SponsorBlock**: Automatically skip sponsored segments, intros, and outros.
- **Playlist Support**: Batch download entire playlists with regex filtering.
- **Metadata & Thumbnails**: Embed high-quality metadata and thumbnails.

### ☁️ Connectivity
- **Cloud Upload**: Auto-upload finished downloads to Google Drive.
- **RSS Feed Manager**: Subscribe to channels and auto-download new content.
- **Discord RPC**: Show off your downloading status to friends.

## 🚀 Installation

### 📦 Binary Releases (Recommended)
We provide standalone executable binaries for Windows, Linux, and macOS. No Python installation required.
1. Go to the **[Releases](../../releases)** page.
2. Download the version for your OS (`StreamCatch.exe` for Windows, `StreamCatch` for Linux/Mac).
3. Run the file.

### 🐳 Docker (Web Interface)
Run StreamCatch as a self-hosted web service:
```bash
docker-compose up -d
```
Access the UI at `http://localhost:8550`. Downloads are saved to `./downloads`.

### 💻 Source (Developers)

#### Prerequisites
- Python 3.8+
- FFmpeg (required for post-processing)

#### Setup
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/AmirrezaFarnamTaheri/StreamCatch.git
    cd StreamCatch
    ```
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the application**:
    ```bash
    python main.py
    ```

#### One-Click Scripts
- **Windows**: `install-and-run.bat`
- **Linux/macOS**: `install-and-run.sh`

## 📱 Mobile Support
StreamCatch runs on iOS and Android via Flet. See [SETUP_MOBILE.md](SETUP_MOBILE.md) for details.

## 📖 User Guide

### Managing the Queue
- **Add**: Paste a URL and click "Fetch Info", then "Add to Queue".
- **Clipboard Monitor**: Toggle the switch at the top right to auto-capture copied URLs.
- **Batch Import**: Import a list of URLs from a text file.
- **Schedule**: Set a specific time for downloads to start.
- **Reorder**: Use Up/Down arrows to manage priority.

### Download Options
- **Video/Audio Quality**: Select specific formats.
- **Force Generic/Direct**: Check this box to bypass video extraction and download the URL directly as a file.
- **Subtitles**: Select language to embed.

### Dashboard
- View total download count and statistics.
- Monitor recent activity.

### Configuration
Settings are persisted in `~/.streamcatch/config.json`. You can configure:
- Proxy settings
- Download rate limits
- Output templates (e.g., `%(title)s.%(ext)s`)
- GPU acceleration preference

## 🤝 Contributing
We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

### Running Tests
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## 📄 License
GNU General Public License v3.0. See `LICENSE` for details.
