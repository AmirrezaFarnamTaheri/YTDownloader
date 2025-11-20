# What's Next for YTDownloader

This document outlines the roadmap for future development, identifying key areas for improvement and expansion.

## 🚀 Feature Expansion

### Backend
*   **FFmpeg Integration:**
    *   Ensure FFmpeg is bundled or properly detected for advanced post-processing (merging video/audio, converting formats).
    *   Add a UI indicator for FFmpeg availability.
*   **Advanced Download Options:**
    *   Support for specific time range downloads (clipping).
    *   Audio metadata editing (ID3 tags for MP3s).
    *   Thumbnail embedding in audio files.
*   **Authentication Manager:**
    *   More robust handling of cookies.txt.
    *   Integrated "Login" flow (via webview or browser extension bridge) to capture cookies automatically.

### Frontend (Desktop)
*   **Download Manager History:**
    *   Persistent database (SQLite) of past downloads.
    *   Ability to retry failed downloads from history.
*   **Queue Management:**
    *   Drag-and-drop reordering of queue items.
    *   Priority settings (High, Normal, Low).
*   **Visualizations:**
    *   Real-time graphing of download speeds.
    *   Disk space usage indicator.

### Mobile (Android/iOS)
*   **Native Integration:**
    *   "Share to" functionality (share YouTube link from YouTube app to YTDownloader).
    *   Background service for downloads.
*   **UI Polish:**
    *   Complete the KivyMD interface to match the desktop feature set.

## 🛠 Technical Debt & Infrastructure

### Testing
*   **Integration Tests:**
    *   Create a suite of tests that actually download small test files (using a local mock server or stable external test vectors) to verify the full pipeline.
*   **Cross-Platform Testing:**
    *   Automated CI pipelines for Windows, Linux, and macOS builds.

### Security
*   **Input Sanitization:**
    *   Review all user inputs (filenames, URLs) to prevent command injection or path traversal, although `yt-dlp` handles much of this, extra layers are safer.
*   **Dependency Scanning:**
    *   Automated vulnerability scanning for `requirements.txt`.

## 📦 Distribution

*   **Auto-Update Mechanism:**
    *   Implement a check-for-updates feature that downloads the latest EXE/APK from GitHub Releases.
*   **Signed Binaries:**
    *   Obtain code signing certificates to prevent "Unknown Publisher" warnings on Windows and macOS.
