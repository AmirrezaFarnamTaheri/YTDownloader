# StreamCatch 🎥

**StreamCatch** (formerly YTDownloader) is a modern, robust, and feature-rich media downloader built with [Flet](https://flet.dev) (Flutter for Python) and [yt-dlp](https://github.com/yt-dlp/yt-dlp). It supports downloading videos and audio from thousands of websites, including YouTube, Telegram, Twitter/X, Instagram, and generic file hosts.

![StreamCatch Banner](assets/logo.svg)

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

## 🚀 Installation

### Desktop (Windows/Linux/macOS)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/streamcatch.git
    cd streamcatch
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: You also need `ffmpeg` installed and in your system PATH.*

3.  **Run the application:**
    ```bash
    python main.py
    ```

### Mobile (Android/iOS)

See [MOBILE_DEPLOYMENT.md](MOBILE_DEPLOYMENT.md) for detailed build instructions using `flet build`.

## 🛠️ Architecture

The project is structured for modularity and robustness:

*   **`main.py`**: Entry point and Flet UI initialization.
*   **`downloader/`**: Core download logic package.
    *   `core.py`: Main orchestration logic.
    *   `info.py`: Metadata fetching.
    *   `engines/`: Specific download engines (yt-dlp, generic).
    *   `extractors/`: Specific extractors (Telegram, Generic).
*   **`queue_manager.py`**: Thread-safe queue management with atomic operations.
*   **`tasks.py`**: Background worker logic handling the download lifecycle.
*   **`views/`**: Modular UI components (Download, Queue, History, etc.).
*   **`components/`**: Reusable UI widgets.

## 🧪 Testing

Run the test suite to ensure robustness:

```bash
# Run all unit tests
python -m unittest discover tests

# Run specific tests
python -m unittest tests/test_pipeline_integration.py
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
