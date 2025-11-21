# Lumina - Modern Media Downloader

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Status](https://img.shields.io/badge/status-stable-green)

**Lumina** (formerly YTDownloader) is a modern, cross-platform desktop application for downloading videos and audio from YouTube and other supported sites.

> **New in v3.0**: Fully rewritten UI using [Flet](https://flet.dev) (Flutter for Python) for a smoother, responsive experience with glassmorphism effects and fluid animations.

## 🌟 Features

*   **Modern UI**: New Flet-based interface with Dark Mode, Glassmorphism, and responsive layout.
*   **Cinema Mode**: Minimalist focus view for monitoring downloads.
*   **Interactive Queue**: Drag-and-drop reordering, easy management.
*   **Dashboard Analytics**: Visual stats for your downloads.
*   **High Quality**: Download up to 4K/8K video and high-bitrate audio.
*   **SponsorBlock**: Automatically remove sponsored segments.
*   **Batch Downloading**: Import URLs from a text file.
*   **Scheduler**: Schedule downloads for later.
*   **RSS Feed Support**: Subscribe to channels and auto-download (coming soon).
*   **Advanced Options**: Proxy support, rate limiting, metadata embedding.

## 🚀 Installation

### One-Click Installers
*   **Windows**: Run `install-and-run.bat` (or `install-and-run.ps1`).
*   **Linux/macOS**: Run `install-and-run.sh`.

### Manual Setup
1.  **Clone the repo**:
    ```bash
    git clone https://github.com/yourusername/Lumina.git
    cd Lumina
    ```
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run**:
    ```bash
    python main.py
    ```

**Note**: You must have [FFmpeg](https://ffmpeg.org/) installed and available in your system PATH for audio conversion and video merging features.

## 📖 Documentation

See the [WIKI](WIKI.md) for a comprehensive user guide.
Check [SUGGESTIONS.md](SUGGESTIONS.md) for future roadmap ideas.

## 🛠 Development

Run tests:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## 🤝 Contributing

Contributions are welcome! Please check `CONTRIBUTING.md` for guidelines.
