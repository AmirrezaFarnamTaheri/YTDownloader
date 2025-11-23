# StreamCatch Wiki

## 📚 User Guide

### 1. Getting Started
- **Installation**: Download the installer for your OS from the Releases page. Run it to install StreamCatch.
- **First Launch**: Open StreamCatch. You'll see the main Dashboard.

### 2. Downloading Media
- **Standard Download**: Paste a URL (YouTube, Twitter, etc.) into the "Video URL" box. Click **Fetch Info**.
    - Select your desired Quality and Format.
    - Click **Add to Queue**.
- **Batch Import**: Click the 📁 (Folder) icon in the header. Select a `.txt` file containing URLs (one per line).
- **Scheduling**: Click the ⏰ (Clock) icon to set a time. The next download added will be scheduled for that time.

### 3. Queue Management
- **Monitoring**: Watch progress bars, speed, and ETA in the Queue tab.
- **Reordering**: Use the Up/Down arrows to prioritize specific downloads.
- **Control**: Cancel or Retry failed downloads.

### 4. Advanced Features
- **Browser Cookies**: Select your browser (Chrome, Firefox, etc.) to use its cookies. This helps download age-gated or premium content.
- **SponsorBlock**: Automatically skip/remove sponsored segments in YouTube videos.
- **RSS Feeds**: Add RSS URLs to the RSS tab to auto-download new videos from channels.
- **Clipboard Monitor**: Enable in the sidebar. The app will verify any copied URL and prompt to download it.

## 🔧 Technical Documentation

### Architecture
StreamCatch uses a modular architecture:
- **Frontend**: Flet (Python wrapper for Flutter).
- **Backend**: Python 3.12+.
- **Core Engine**: `yt-dlp` (custom build recommended).

### Key Modules
1.  **`main.py`**: Application entry point. Handles UI threading and global state.
2.  **`downloader` Package**:
    -   `core.py`: The brain. Decides which engine to use.
    -   `engines/ytdlp.py`: Wrapper for yt-dlp.
    -   `engines/generic.py`: Custom HTTP downloader for direct files.
    -   `extractors/telegram.py`: Scrapes `t.me` public pages.
3.  **`queue_manager.py`**: Thread-safe manager using `threading.Lock()` to ensure data integrity during concurrent operations.
4.  **`app_state.py`**: Singleton state management (cleaner than global variables).

### Robustness Strategies
1.  **Race Condition Prevention**: All shared resources (Queue, History) are protected by locks.
2.  **Fallback Logic**:
    -   *Strategy 1*: `yt-dlp` (Video Platforms).
    -   *Strategy 2*: `TelegramExtractor` (if URL matches `t.me`).
    -   *Strategy 3*: `GenericExtractor` (HEAD request to check for direct file).
    -   *Strategy 4*: `Force Generic` mode (User override).
3.  **Error Handling**: Every network call is wrapped in try/except blocks with logging.

### Build & Deployment
- **Windows**: Uses Inno Setup (`installers/setup.iss`) to create a professional `.exe` installer.
- **Linux**: Uses PyInstaller and `dpkg-deb` to create a `.deb` package.
- **CI/CD**: GitHub Actions workflows (`build-windows.yml`, `build-linux.yml`) automatically build and release on tags.

### Extending StreamCatch
- **Adding a new View**: Create a class in `views/` inheriting from `BaseView`. Add it to `main.py`.
- **Adding a new Downloader**: Implement a new Engine in `downloader/engines/` and register it in `downloader/core.py`.
