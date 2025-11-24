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

## 🚀 Installation & Building

### Pre-built Installers
Check the **Releases** page for the latest installers for Windows (`.exe`) and Linux (`.deb`).

### Building from Source

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

3.  **Run Development Version:**
    ```bash
    python main.py
    ```

4.  **Build Installer (Windows/Linux):**
    To create a standalone executable or installer:
    ```bash
    python scripts/build_installer.py
    ```
    - On **Windows**, this requires Inno Setup to generate the `.exe` installer (otherwise it just creates the standalone binary).
    - On **Linux**, this uses PyInstaller to create a binary in `dist/`.

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
# Run all unit tests with coverage
pytest --cov=.
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Distributed under the GNU Affero General Public License v3.0 (AGPLv3). See `LICENSE` for more information.
