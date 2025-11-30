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
Grab the latest release artifacts:
- Windows installer: `StreamCatch-Windows-Installer.exe`
- Linux package: `StreamCatch-Linux-amd64.deb`
- macOS image: `StreamCatch-macOS.dmg`

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

4.  **Build Installers (desktop):**
    To create platform binaries locally:
    ```bash
    python scripts/build_installer.py
    ```
    - The script uses **Nuitka** to compile the application into a native binary.
    - On **Windows**, install Inno Setup (`iscc`) to produce the `.exe` installer; otherwise only the executable is created.
    - On **Linux**, Nuitka writes the binary to `dist/streamcatch`. The GitHub Action workflow creates a `.deb` package.
    - On **macOS**, Nuitka generates `dist/StreamCatch.app`; this can be wrapped into a `.dmg`.

### Mobile (Android/iOS)

Mobile builds are handled via `flet build` commands or GitHub Actions.
- **Android**: `flet build apk`
- **iOS**: `flet build ipa`

### Optional: Discord Rich Presence
Set `DISCORD_CLIENT_ID` in your environment to enable Discord Rich Presence updates. Without it, social integration stays disabled gracefully.

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

The test suite includes extensive coverage for:
- **Thread-safety** of the queue manager and `AppState` singleton.
- **Downloader core** behaviors (Telegram, force-generic, yt-dlp options, GPU, rate limits).
- **Security safeguards** around history storage and basic path/template validation.

## 📝 Crash Reports

If StreamCatch encounters an unexpected error, it writes a detailed crash report to:
- **Windows/Linux/macOS**: `~/.streamcatch/crash.log`

On Windows, a native error dialog is also shown. When reporting issues, please attach the relevant section of `crash.log` (redact any sensitive paths or URLs).

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Distributed under the GNU Affero General Public License v3.0 (AGPLv3). See `LICENSE` for more information.
