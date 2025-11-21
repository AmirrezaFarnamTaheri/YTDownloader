# StreamCatch - Modern Media Downloader

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Status](https://img.shields.io/badge/status-stable-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

**StreamCatch** (formerly Lumina/YTDownloader) is a modern, cross-platform desktop application for downloading videos and audio from YouTube and other supported sites.

> **New in v3.0**: Fully rewritten UI using [Flet](https://flet.dev) (Flutter for Python) for a smoother, responsive experience.
> **New in v4.0**: Docker support, Performance Acceleration (Aria2c/GPU), and Enhanced Accessibility.

## 🌟 Features

*   **Modern UI**: New Flet-based interface with Dark Mode and Cinema Mode.
*   **Performance**:
    *   **Aria2c Integration**: Multi-threaded downloading for max speed.
    *   **GPU Acceleration**: Hardware encoding support (NVENC/VAAPI).
*   **Smart Features**:
    *   **Time Range / Cut**: Download specific parts (Start/End time).
    *   **SponsorBlock**: Automatically remove sponsored segments.
*   **Interactive Queue**: Keyboard navigation (J/K/D/Space) and reordering.
*   **Multi-Platform**: Windows, Linux, macOS, iOS, Android, and **Docker**.
*   **Cloud & Social**: Google Drive upload, Discord Rich Presence.

## 🚀 Quick Start

### 🐳 Docker (Recommended for Servers/NAS)
Run StreamCatch as a web service accessible from any browser on your network.

1.  **Run with Docker Compose**:
    ```bash
    docker-compose up -d
    ```
2.  Open your browser to `http://localhost:8550`.
3.  Downloads are saved to the `./downloads` folder on your host.

### 📱 Mobile (iOS/Android)
StreamCatch supports running on mobile via the Flet app.
See [SETUP_MOBILE.md](SETUP_MOBILE.md) for instructions.

### 💻 Desktop (Windows/Mac/Linux)

#### One-Click Installers
*   **Windows**: Run `install-and-run.bat` (or `install-and-run.ps1`).
*   **Linux/macOS**: Run `install-and-run.sh`.

#### Manual Setup
1.  **Clone the repo**:
    ```bash
    git clone https://github.com/yourusername/StreamCatch.git
    cd StreamCatch
    ```
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run**:
    ```bash
    python main.py
    ```

**Note**: You must have [FFmpeg](https://ffmpeg.org/) installed for full functionality.

## 📖 Documentation

*   [WIKI](WIKI.md): Comprehensive user guide.
*   [WHATS_NEXT](WHATS_NEXT.md): Roadmap (v4.0 features).
*   [SETUP_MOBILE](SETUP_MOBILE.md): Mobile installation guide.

## 🛠 Development

Run tests:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## 🤝 Contributing

Contributions are welcome! Please check `CONTRIBUTING.md` for guidelines.
