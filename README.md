# StreamCatch 🎥

**StreamCatch** (formerly YTDownloader) is a modern, robust, and feature-rich media downloader built with [Flet](https://flet.dev) (Flutter for Python) and [yt-dlp](https://github.com/yt-dlp/yt-dlp). It supports downloading videos and audio from thousands of websites, including YouTube, Telegram, Twitter/X, Instagram, and generic file hosts.

![StreamCatch Banner](assets/logo.svg)

## 📚 Documentation

Detailed documentation is available in our **[Wiki](wiki/Home.md)**:

*   **[Architecture](wiki/Architecture.md)**: High-level system design and component interactions.
*   **[Core Concepts](wiki/Concepts.md)**: Explanation of key concepts like Downloaders, Extractors, and Managers.
*   **[API Reference](wiki/API.md)**: Internal API documentation for developers.
*   **[Troubleshooting](wiki/Troubleshooting.md)**: Solutions to common issues.

## ✨ Features

*   **Modern UI/UX**: Built with Material Design 3, responsive layout, and a soulful dark theme.
*   **Robust Downloading**: Powered by `yt-dlp` for maximum compatibility.
*   **Platform Agnostic**: Runs on **Windows**, **Linux**, **macOS**, **Android**, and **iOS**.
*   **Advanced Queuing**:
    *   Batch downloading
    *   Priority reordering
    *   Scheduling (download later)
    *   Concurrency management
*   **Special Integrations**:
    *   **Telegram Scraper**: Download directly from public `t.me` links.
    *   **Generic Downloader**: Fallback for direct file links with multi-threaded downloading.
*   **Performance**:
    *   GPU Acceleration (CUDA/Vulkan) support.
    *   Aria2c external downloader integration for speed.
*   **RSS Feeds**: Monitor channels and download latest videos.
*   **Clipboard Monitor**: Automatically detect copied links.
*   **SponsorBlock**: Skip non-content segments automatically.

## 🚀 Installation & Building

See the [Troubleshooting Guide](wiki/Troubleshooting.md) for common installation issues.

### Quick Start (Source)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/streamcatch.git
    cd streamcatch
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run:**
    ```bash
    python main.py
    ```

## 🧪 Testing

Run the test suite to ensure robustness:

```bash
# Run all unit tests with coverage
pytest --cov=.
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Distributed under the GNU Affero General Public License v3.0 (AGPLv3). See `LICENSE` for more information.
