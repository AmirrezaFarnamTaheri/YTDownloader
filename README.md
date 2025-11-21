# StreamCatch - Modern Media Downloader

![License](https://img.shields.io/badge/license-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Status](https://img.shields.io/badge/status-stable-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

**StreamCatch** is a professional-grade, cross-platform media downloader designed for robustness, speed, and aesthetics. Built with Python and Flet, it offers a modern Material Design 3 interface with advanced features for power users.

## 👤 Credits

*   **Author**: Amirreza "Farnam" Taheri
*   **Contact**: taherifarnam@gmail.com
*   **Github**: [AmirrezaFarnamTaheri](https://github.com/AmirrezaFarnamTaheri)

## 🌟 Key Features

### 🎨 Modern & Immersive UI
- **Navigation Rail**: Clean sidebar navigation for quick access to Queues, History, and Settings.
- **Cinema Mode**: An immersive, distraction-free overlay for monitoring active downloads.
- **Dashboard**: Real-time analytics and download statistics.
- **Card-Based Design**: Beautiful, responsive cards for download items with progress visualization.

### ⚡ Performance & Robustness
- **Multi-threaded Queue**: A thread-safe `QueueManager` ensures stability even under heavy load.
- **Aria2c Integration**: Accelerate downloads with multi-connection support.
- **GPU Acceleration**: Hardware-accelerated encoding/decoding (NVENC/VAAPI/QSV) via FFmpeg.
- **Smart Resume**: Robust error handling and resume capabilities for interrupted downloads.

### 🛠 Advanced Tools
- **Time Range**: Download specific clips (Start/End time) without downloading the full video.
- **SponsorBlock**: Automatically skip sponsored segments, intros, and outros.
- **Playlist Support**: Batch download entire playlists with regex filtering.
- **Metadata & Thumbnails**: Embed high-quality metadata and thumbnails.

### ☁️ Connectivity
- **Cloud Upload**: Auto-upload finished downloads to Google Drive.
- **RSS Feed Manager**: Subscribe to channels and auto-download new content.
- **Discord RPC**: Show off your downloading status to friends.

## 🚀 Quick Start

### 🐳 Docker (Web Interface)
Run StreamCatch as a self-hosted web service:
```bash
docker-compose up -d
```
Access the UI at `http://localhost:8550`. Downloads are saved to `./downloads`.

### 💻 Desktop (Windows/Mac/Linux)

#### Prerequisites
- Python 3.8+
- FFmpeg (required for post-processing)

#### Installation
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
- **Reorder**: Use Up/Down arrows.
- **Prioritize**: The queue processes items sequentially unless concurrent downloading is enabled.

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
