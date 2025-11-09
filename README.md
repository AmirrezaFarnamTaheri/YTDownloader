# YTDownloader - Advanced YouTube Video Downloader

YTDownloader is a modern, feature-rich desktop application for downloading videos and subtitles from YouTube. Built with Python, Tkinter, and the powerful `yt-dlp` library, it offers a seamless, intuitive, and production-quality experience for all your video downloading needs.

**Latest Version**: 2.0 (Comprehensive Refactor & Quality Improvements)

## Key Features

### Core Functionality
- **Modern & Intuitive UI**: Clean, responsive interface with light/dark theme support and persistent theme preference
- **Download Queue Management**: Queue multiple videos with pause, resume, and cancel controls
- **Enhanced Download Queue**: Real-time tracking of file size, download speed, and ETA for each download
- **Detailed Format Selection**: Browse video and audio formats with complete specifications (resolution, FPS, codecs, file size)

### Advanced Features
- **Chapter Splitting**: Automatically split videos into chapters for easier navigation and editing
- **Subtitle & Transcript Support**: Download subtitles in multiple formats (SRT, VTT, ASS) and languages
- **Playlist Support**: Download entire playlists with a single click
- **Proxy Configuration**: Use HTTP/SOCKS proxies for downloads
- **Speed Limiting**: Configure download bandwidth limits (e.g., 50K, 4.2M, 1.5G)
- **Custom Output Paths**: Full control over where files are saved
- **Configurable Settings**: Settings persist between sessions

### Quality & Reliability
- **Comprehensive Input Validation**: URL, proxy, rate limit, and path validation
- **Robust Error Handling**: User-friendly error messages with detailed logging
- **Exception Safety**: Graceful handling of network errors, invalid inputs, and edge cases
- **Progress Tracking**: Real-time visual progress bar with status updates
- **Configuration Persistence**: Theme and settings saved to `~/.ytdownloader/config.json`

### Developer Features
- **Type Hints**: Full Python type annotations for better code quality
- **Comprehensive Logging**: DEBUG and INFO level logging to `ytdownloader.log`
- **Extensive Test Coverage**: 40+ unit tests covering core functionality and edge cases
- **Clean Architecture**: Separation of concerns (GUI, downloader, validation)
- **Standalone Executable**: Single executable with no external dependencies required

## User Walkthrough

Here’s a step-by-step guide to using YTDownloader:

1.  **Enter a Video URL**: Paste the URL of the YouTube video or playlist you want to download into the "Video URL" field.

2.  **Fetch Video Info**: Click the "Fetch Info" button to see the video's title, thumbnail, and duration, as well as a list of available video, audio, and subtitle options.

3.  **Select Your Options**:
    *   **Video Tab**: Choose your desired video format from the dropdown menu. You'll see detailed information about each format, including the resolution, FPS, codecs, and file size.
    *   **Audio Tab**: Choose your desired audio format from the dropdown menu, with details like bitrate, codec, and file size.
    *   **Subtitles Tab**: If subtitles are available, select your preferred language and format.
    *   **Playlist Tab**: If you entered a playlist URL, check the "Download Playlist" box to download the entire playlist.
    *   **Chapters Tab**: Check the "Split Chapters" box to split the video into chapters.
    *   **Settings Tab**: Configure a proxy and download speed limit.

4.  **Choose an Output Path**: Click the "Browse..." button to select the folder where you want to save your download. If you don't choose a path, the file will be saved in the same directory as the application.

5.  **Start the Download**: Click the "Add to Queue" button to add the video to the download queue. The download will start automatically.

6.  **Manage Your Downloads**:
    *   **Pause/Resume/Cancel**: Use the "Pause," "Resume," and "Cancel" buttons to control your downloads.
    *   **Downloads Tab**: Switch to the "Downloads" tab to see a detailed view of your download queue, including the file size, download speed, and ETA.
    *   **Context Menu**: Right-click on a download in the "Downloads" tab to open a context menu with options to cancel, remove the download from the queue, or open the file's location.

7.  **Clear the UI**: When you're finished, click the "Clear" button to reset the UI and prepare for a new download.

## Quick Start

### Option 1: Download Pre-Built Executable (Recommended)

Download the latest standalone executable from the [Releases](../../releases) page. No installation required—just run the `.exe` file.

### Option 2: Run from Source Code

**Requirements**: Python 3.8+

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/AmirrezaFarnamTaheri/YTDownloader.git
   cd YTDownloader
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   ```bash
   python main.py
   ```

### Option 3: Build Your Own Executable

1. Follow steps 1-3 above
2. Build the executable:
   ```bash
   pyinstaller --onefile --windowed --noconsole --icon=icon.ico main.py
   ```
   The executable will be in the `dist/` directory.

## System Requirements

- **Python**: 3.8 or higher
- **OS**: Windows, macOS, or Linux
- **RAM**: 256 MB minimum
- **Disk Space**: 50 MB for installation
- **Internet**: Required for downloading videos

## Configuration

Settings are automatically saved to:
- **Linux/macOS**: `~/.ytdownloader/config.json`
- **Windows**: `C:\Users\<username>\.ytdownloader\config.json`

Configuration includes:
- Theme preference (light/dark)
- (Extensible for future settings)

Logs are saved to `ytdownloader.log` in the current working directory.

## Testing

Run the comprehensive test suite:

```bash
# Using unittest (included with Python)
python -m unittest discover -s tests -p "test_*.py" -v

# Using pytest (if installed)
pytest tests/ -v --tb=short
```

### Test Coverage

The project includes 40+ unit tests covering:
- **Downloader Module** (13 tests):
  - Video info fetching with various format combinations
  - Download configuration (subtitles, chapters, proxies, rate limits)
  - Error handling (network errors, invalid URLs, user cancellation)
  - Edge cases (no subtitles, mixed formats, large playlists)

- **GUI Module** (20+ tests):
  - Input validation (URLs, proxies, rate limits, paths)
  - Queue management (add, remove, cancel operations)
  - UI state management and interactions
  - Error handling and user feedback

- **Utility Functions** (10+ tests):
  - URL validation
  - Proxy format validation
  - Rate limit format validation
  - File size formatting with various units

## Architecture

### Project Structure

```
YTDownloader/
├── main.py              # GUI implementation (Tkinter)
├── downloader.py        # Core download logic (yt-dlp wrapper)
├── requirements.txt     # Python dependencies
├── tests/
│   ├── test_gui.py      # GUI unit tests
│   └── test_downloader.py # Downloader unit tests
├── README.md            # This file
├── CONTRIBUTING.md      # Contribution guidelines
├── CODE_OF_CONDUCT.md   # Community guidelines
└── SECURITY.md          # Security policy
```

### Key Components

**main.py - GUI (750+ lines)**
- `CancelToken`: Manages download cancellation and pause/resume
- `YTDownloaderGUI`: Main application window with tabbed interface
- Validation functions: URL, proxy, rate limit, path validation
- Utility functions: File size formatting, config management

**downloader.py - Core Logic (190+ lines)**
- `get_video_info()`: Fetches video metadata without downloading
- `download_video()`: Handles actual video download with all options
- Error handling with proper logging

**Features**:
- Type hints throughout for better code quality
- Comprehensive logging to `ytdownloader.log`
- Configuration persistence in `~/.ytdownloader/config.json`
- Thread-safe UI queue for worker thread communication
- Proper exception handling and user feedback

## Recent Improvements (v2.0)

### Critical Bugfixes
- Fixed CancelToken missing `is_paused` initialization (AttributeError)
- Fixed file size division by zero when `filesize` is None
- Fixed unsafe format ID parsing using fragile string split
- Fixed IndexError crashes in queue operations
- Added proper exception handling in all critical operations

### Code Quality
- Added comprehensive type hints (main.py, downloader.py)
- Added proper Google-style docstrings
- Refactored configuration management
- Improved error messages for better UX
- Added extensive logging (INFO and DEBUG levels)

### Input Validation & Security
- URL validation (protocol and length checks)
- Proxy format validation (must have protocol and port)
- Rate limit format validation (K, M, G, T units)
- Output path existence validation
- File size validation with safe conversion

### User Experience
- Set minimum window size (900x700)
- Improved title and window descriptions
- Added status messages showing queue size
- Added confirmation dialogs for destructive operations
- Better error dialog messages with log file references
- Theme preference persisted between sessions

### Testing & Documentation
- Increased from ~40 to 400+ lines of tests
- 23 validation function tests
- 14 GUI functionality tests
- 13 downloader tests
- Comprehensive README with examples
- Updated requirements.txt with versions

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'yt_dlp'"
**Solution**: Install dependencies: `pip install -r requirements.txt`

### Issue: "No theme for system"
**Solution**: The application will use default theme. Ensure `sv-ttk` or `ttkbootstrap` is installed.

### Issue: Downloads fail with "Network error"
**Solution**: Check your internet connection or try using a proxy in Settings tab.

### Issue: "Permission denied" when saving files
**Solution**: Ensure the output directory exists and has write permissions.

### Issue: Application crashes on startup
**Solution**: Check `ytdownloader.log` for detailed error information. Ensure Python 3.8+.

### Issue: Proxy not working
**Solution**: Verify proxy format is `protocol://host:port` (e.g., `http://proxy.com:8080`)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The powerful video downloader
- [Tkinter](https://docs.python.org/3/library/tkinter.html) - Python's GUI toolkit
- [sv-ttk](https://github.com/TkinterEP/ttkbootstrap) - Modern theme support
