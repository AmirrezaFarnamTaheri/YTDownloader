# StreamCatch Wiki

## 📚 User Guide

### 1. Getting Started
- **Installation**: Download the installer for your OS from the Releases page. Run it to install StreamCatch.
- **First Launch**: Open StreamCatch. You'll see the main Dashboard.
- **System Requirements**:
  - Windows 10/11 or modern Linux distribution (Debian/Ubuntu recommended).
  - Internet connection for downloading media.
  - ~200MB free disk space for the application.
  - FFmpeg installed (bundled with Windows installer, usually required on Linux).

### 2. Downloading Media
- **Standard Download**: Paste a URL (YouTube, Twitter, etc.) into the "Video URL" box. Click **Fetch Info**.
    - Select your desired Quality (e.g., 1080p, 720p) and Format (MP4, MP3, etc.).
    - Click **Add to Queue**.
- **Batch Import**: Click the 📁 (Folder) icon in the header. Select a `.txt` file containing URLs (one per line).
- **Scheduling**: Click the ⏰ (Clock) icon to set a time. The next download added will be scheduled for that time.
- **Force Generic Download**: Toggle this switch if a specific site is failing with the standard engine. It attempts a direct file download.

### 3. Queue Management
- **Monitoring**: Watch progress bars, speed, and ETA in the Queue tab.
- **Reordering**: Use the Up/Down arrows to prioritize specific downloads (only available for Queued items).
- **Control**: Cancel active downloads or Retry failed/cancelled ones.
- **Clear Queue**: Remove completed items to declutter the view.

### 4. Advanced Features
- **Browser Cookies**: Select your browser (Chrome, Firefox, etc.) to use its cookies. This helps download age-gated or premium content that you have access to in your browser.
- **SponsorBlock**: Automatically skip/remove sponsored segments in YouTube videos.
- **RSS Feeds**: Add RSS URLs to the RSS tab to auto-download new videos from channels.
- **Clipboard Monitor**: Enable in the sidebar. The app will verify any copied URL and prompt to download it (requires `pyperclip`).
- **Proxy Support**: Configure HTTP/SOCKS proxies in Settings for privacy or bypassing restrictions.

### 5. Troubleshooting
| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| **Download Fails Immediately** | Invalid URL or Geoblocking | Check URL in browser. Use VPN/Proxy. Try "Force Generic". |
| **"ffmpeg not found"** | Missing dependency | Linux: `sudo apt install ffmpeg`. Windows: Reinstall StreamCatch. |
| **Slow Downloads** | Rate Limit or throttling | Check Settings > Rate Limit. Use "Browser Cookies" feature. |
| **"Sign in to confirm..."** | Age-gated content | Use "Browser Cookies" (e.g., Chrome) in Download tab. |
| **App Crashes** | Database corruption or Bug | Check `ytdownloader.log`. Backup/Delete `~/.streamcatch/history.db`. |

### 6. Localization
StreamCatch supports multiple languages.
- **Current Languages**: English (default).
- **Adding a Language**:
    1. Create a new JSON file in `locales/` (e.g., `es.json`).
    2. Copy keys from `en.json`.
    3. Translate values.
    4. Submit a Pull Request!

---

## 🔧 Technical Documentation

### Architecture
StreamCatch uses a modular architecture:
- **Frontend**: Flet (Python wrapper for Flutter) providing a responsive, cross-platform UI.
- **Backend**: Python 3.12+ handling logic, file I/O, and networking.
- **Core Engine**: `yt-dlp` (custom build recommended) for media extraction, with a custom generic fallback.

### Key Modules
1.  **`main.py`**: Application entry point. Initializes `AppState`, `QueueManager`, and the Flet UI. Handles the main event loop.
2.  **`downloader` Package**:
    -   `core.py`: The orchestration logic. Decides which engine/extractor to use based on URL and settings.
    -   `engines/ytdlp.py`: robust wrapper for `yt-dlp`. Handles options injection (cookies, progress hooks).
    -   `engines/generic.py`: Custom HTTP downloader using `requests` with streaming. Supports resume (Range headers) and retries.
    -   `extractors/telegram.py`: Scrapes `t.me` public pages for video links.
3.  **`queue_manager.py`**: Thread-safe manager using `threading.Lock()` to ensure data integrity during concurrent operations. Implements the producer-consumer pattern for the download queue.
4.  **`app_state.py`**: Singleton state management using a global `AppState` object.
5.  **`config_manager.py`**: Handles loading/saving `config.json` with atomic writes to prevent corruption.
6.  **`history_manager.py`**: SQLite-based history tracking. Thread-safe with retry logic for database locks.

### Robustness Strategies
1.  **Race Condition Prevention**: All shared resources (Queue, History, Config) are protected by locks or atomic operations.
2.  **Fallback Logic**:
    -   *Strategy 1*: `TelegramExtractor` (priority for `t.me` URLs).
    -   *Strategy 2*: `yt-dlp` (Video Platforms - primary engine).
    -   *Strategy 3*: `GenericExtractor` (HEAD request to check for direct file).
    -   *Strategy 4*: `Generic Engine` (Fallback if yt-dlp fails).
3.  **Error Handling**: comprehensive try/except blocks. Network operations have timeouts and retry logic with exponential backoff.
4.  **Input Validation**: rigorous validation of URLs, file paths, and configuration values to prevent injection or crashes.

### Configuration & Data
- **Config File**: Located at `~/.streamcatch/config.json`. Stores user preferences.
- **Database**: `~/.streamcatch/history.db`. Stores download history.
- **Logs**: `ytdownloader.log` (in run directory). Useful for debugging.

### Development Environment Setup
1.  **Prerequisites**: Python 3.12+, git, ffmpeg.
2.  **Clone**: `git clone <repo_url>`
3.  **Virtual Env**: `python -m venv venv && source venv/bin/activate` (or `venv\Scripts\activate` on Windows).
4.  **Install**: `pip install -r requirements.txt`.
5.  **Run**: `python main.py`.
6.  **Test**: `python -m pytest` (ensures 100% coverage).
7.  **Lint**: `pylint .`

### Build & Deployment
- **Windows**: Uses Inno Setup (`installers/setup.iss`) to create a professional `.exe` installer.
- **Linux**: Uses PyInstaller and `dpkg-deb` to create a `.deb` package.
- **CI/CD**: GitHub Actions workflows (`build-windows.yml`, `build-linux.yml`) automatically build and release on tags.

### Extending StreamCatch
- **Adding a new View**: Create a class in `views/` inheriting from `BaseView`. Add it to `main.py`.
- **Adding a new Downloader**: Implement a new Engine in `downloader/engines/` and register it in `downloader/core.py`.
