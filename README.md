# YTDownloader

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

**YTDownloader** is a modern, powerful, and feature-rich desktop application for downloading videos and audio from YouTube and other supported sites. It leverages `yt-dlp` for robust extraction and features a sleek, dark-themed UI built with `sv_ttk`.

## ✨ Key Features

*   **Modern UI:** Clean, responsive interface with dark mode support.
*   **Smart Downloads:**
    *   Download Videos (up to 8K/HDR) or Audio only.
    *   Playlist & Channel support.
    *   Chapter splitting.
    *   Subtitle extraction (multi-language).
*   **Advanced Control:**
    *   **Proxy Support:** For restricted networks.
    *   **Rate Limiting:** Control download speed.
    *   **Cookie Import:** Bypass age restrictions using browser cookies.
*   **Productivity:**
    *   **Queue System:** distinct download manager.
    *   **Clipboard Monitoring:** Auto-detects copied links.
    *   **Toast Notifications:** Non-intrusive status updates.
*   **Cross-Platform:** Windows, Linux, macOS (and Android beta!).

## 🚀 Installation

### Windows (Exe)
Download the latest `YTDownloader.exe` from the [Releases](#) page.

### From Source

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/yourusername/YTDownloader.git
    cd YTDownloader
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: On Linux, you may need to install Tkinter (`sudo apt install python3-tk`).*

3.  **Run:**
    ```bash
    python main.py
    ```

## 📱 Mobile Version (Beta)

A mobile version built with Kivy/KivyMD is available in the `mobile/` directory.
To build for Android, see [mobile/README.md](mobile/README.md).

## 🛠 Development

### Running Tests
```bash
python -m unittest discover tests
```

### Building Executable
```bash
pyinstaller ytdownloader.spec
```

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) (if available) or submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.
