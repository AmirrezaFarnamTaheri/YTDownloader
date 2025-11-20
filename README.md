# YTDownloader

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Status](https://img.shields.io/badge/status-stable-green)

**YTDownloader** is a modern, cross-platform desktop application for downloading videos and audio from YouTube and other supported sites. Built with Python, Tkinter (with `sv_ttk` theme), and `yt-dlp`.

## 🌟 Features

*   **Modern UI**: Dark-themed, responsive interface.
*   **High Quality**: Download up to 4K/8K video and high-bitrate audio.
*   **Batch Downloading**: Import URLs from a text file.
*   **Scheduler**: Schedule downloads for a later time.
*   **Post-Processing**: Automatically recode videos to MP4, MKV, AVI, etc.
*   **Smart History**: Track and manage your downloaded files.
*   **RSS Feed Support**: Auto-check channels for new videos.
*   **Advanced Options**: Proxy support, rate limiting, browser cookies import, and metadata embedding.

## 🚀 Installation

### One-Click Installers
*   **Windows**: Run `install-and-run.bat` (or `install-and-run.ps1`).
*   **Linux/macOS**: Run `install-and-run.sh`.

### Manual Setup
1.  **Clone the repo**:
    ```bash
    git clone https://github.com/yourusername/YTDownloader.git
    cd YTDownloader
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
pytest --cov=. tests/
```

## 🤝 Contributing

Contributions are welcome! Please check `CONTRIBUTING.md` for guidelines.
