# StreamCatch Wiki

Welcome to the **StreamCatch** documentation. StreamCatch is a modern, high-performance media downloader built with Python and Flet. It combines the power of `yt-dlp` with a beautiful, responsive "Soulful V2" user interface.

---

## 📚 User Guide

### 1. Getting Started
- **Installation**: Download the latest installer for your OS from the [Releases Page](https://github.com/your-repo/releases).
    - **Windows**: Run the `.exe` installer.
    - **Linux**: Install the `.deb` package (`sudo dpkg -i streamcatch.deb`).
- **First Launch**: Open StreamCatch. You will be greeted by the Dashboard, showing recent activity and stats.
- **System Requirements**:
  - **OS**: Windows 10/11 or modern Linux distribution (Debian/Ubuntu/Fedora).
  - **Runtime**: Python 3.12+ (bundled in installer).
  - **Dependencies**: `FFmpeg` (essential for merging video/audio).
    - *Windows*: Included in the installer.
    - *Linux*: Install via `sudo apt install ffmpeg`.

### 2. Downloading Media
StreamCatch offers multiple ways to capture content:

#### A. Standard Download
1.  **Paste URL**: Copy a link from YouTube, Twitter, Instagram, TikTok, or Telegram. Paste it into the "Video URL" field on the **Download** tab.
2.  **Fetch Info**: Click the 🔍 (Search) button. StreamCatch will retrieve metadata (Title, Duration, Formats).
3.  **Customize**:
    -   **Video Quality**: Choose from available resolutions (e.g., 1080p, 4k, 720p) or "Best".
    -   **Audio Format**: Extract audio only (MP3, M4A) if desired.
    -   **Subtitles**: Select a language (e.g., `en`, `es`) to embed subtitles.
    -   **Time Range**: Specify Start/End times (e.g., `00:01:30` to `00:02:00`) to download a clip.
4.  **Queue It**: Click **Add to Queue**. The download starts automatically in the background.

#### B. Batch Import
Have a list of links?
1.  Create a `.txt` file with one URL per line.
2.  Click the 📁 (File Upload) icon in the Download tab header.
3.  Select your file. StreamCatch will queue all valid links instantly.

#### C. Scheduling
Plan downloads for later (e.g., off-peak hours):
1.  Click the ⏰ (Clock) icon.
2.  Pick a time.
3.  The *next* item you add to the queue will be scheduled for that time.

#### D. Advanced Options
-   **Force Generic**: Toggle this if a specialized extractor fails. It attempts to download the file directly via HTTP using the Generic extractor.
-   **SponsorBlock**: Automatically skip non-content segments (Sponsors, Intros) on supported platforms.
-   **Proxy**: Configure a proxy in **Settings** to bypass geoblocking.
-   **Rate Limit**: In **Settings**, you can set a limit like `500K`, `2M`, `1G` or with `/s` suffix (e.g. `500K/s`) to throttle download speed.

### 3. Queue Management
Navigate to the **Queue** tab to manage active tasks:
-   **Real-time Stats**: View download speed, ETA, and file size.
-   **Prioritize**: Use the ⬆️/⬇️ arrows to move pending items up or down the list.
-   **Control**: Cancel active downloads or remove completed ones.
-   **Retry**: Failed downloads can be retried with a single click.

### 4. Browser Cookies (Bypassing Restrictions)
Some content (Age-gated, Premium) requires authentication. StreamCatch can borrow cookies from your browser:
1.  In the **Download** tab, look for the "Browser Cookies" dropdown.
2.  Select your browser (e.g., Chrome, Firefox).
3.  StreamCatch will extract cookies from your local browser profile to authenticate the request.
    *   *Note: You must be logged in to the site in that browser, and you should only use this on devices and profiles you trust.*

---

## 🔧 Technical Architecture

StreamCatch is designed for **Robustness**, **modularity**, and **Speed**.

### 🏗️ Core Stack
-   **Language**: Python 3.12 (Typing, Async/Await patterns).
-   **UI Framework**: [Flet](https://flet.dev) (Flutter for Python). Provides a native-feel, 60FPS UI.
-   **Engine**: `yt-dlp` (Media Extraction) + `requests` (Generic Fallback) + `aria2c` (External Accelerator support).
-   **Data**: `SQLite` (WAL mode enabled) for high-concurrency history management.

### 🧩 Module Breakdown

| Module | Responsibility | Key Features |
| :--- | :--- | :--- |
| `main.py` | Entry Point | App lifecycle, Flet page initialization, Global Exception Handling. |
| `downloader.core` | Logic Hub | Orchestrates extraction strategy. Decides between `yt-dlp`, `Telegram`, or `Generic`. |
| `queue_manager.py` | Concurrency | Thread-safe Producer-Consumer queue using `threading.Lock`. Handles status updates atomically. |
| `history_manager.py` | Persistence | SQLite interface with automatic migrations and "Locked" retry logic. |
| `clipboard_monitor` | Background | Watches system clipboard for URLs (Cross-platform via `pyperclip`). |
| `views/` | UI Components | Modular screens (`DownloadView`, `QueueView`, etc.) inheriting from `BaseView`. |

### 🛡️ Robustness & Error Handling
1.  **Atomic Operations**: File writes (`config_manager.py`) use temp files + atomic rename to prevent corruption during crashes.
2.  **Network Resilience**: All HTTP requests use timeouts and exponential backoff retries.
3.  **Fallback Chain**:
    -   `TelegramExtractor` (Specific) -> `yt-dlp` (General Video) -> `GenericExtractor` (Direct File).
4.  **Thread Safety**: The UI runs on the main thread; downloads run in a background thread pool. Communication is handled via callbacks and thread-safe data structures.

### 🚀 Performance Optimization
-   **Lazy Loading**: UI views are initialized only when accessed.
-   **WAL Mode**: SQLite Write-Ahead Logging enables concurrent reads/writes.
-   **Aria2c**: Optional integration for multi-connection downloading (accelerates large files).

---

## 🤝 Contributing & Development

We welcome contributions!

### Setup
```bash
# 1. Clone
git clone https://github.com/your-repo/streamcatch.git
cd streamcatch

# 2. Environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Install
pip install -r requirements.txt

# 4. Run
python main.py
```

### Testing
StreamCatch maintains **100% Code Coverage**.
```bash
# Run all tests
python -m pytest

# Check coverage
python -m pytest --cov=.
```

### Code Style
-   **Formatter**: `black`
-   **Linter**: `pylint`
-   **Type Checker**: `mypy`

### Building Installers
-   **Windows**: Run `scripts/build_installer.py` (Requires Inno Setup).
-   **Linux**: Run `scripts/build_linux.sh` (Requires `dpkg-deb`).

---

## ❓ Troubleshooting

| Problem | Solution |
| :--- | :--- |
| **"ffmpeg not found"** | Install FFmpeg and ensure it's in your system PATH. |
| **Download Stuck at 0%** | Check your internet connection. Try enabling "Force Generic" or changing the Proxy. |
| **"Sign In Required"** | Select your browser in the "Browser Cookies" dropdown to authenticate. |
| **UI Glitches** | Resize the window. If persistent, clear `~/.streamcatch/config.json`. |

---

*StreamCatch © 2025. Built with ❤️ and Python.*
