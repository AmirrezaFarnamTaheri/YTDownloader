# StreamCatch Wiki

Welcome to the StreamCatch Wiki. This documentation covers the architecture, features, and advanced usage of the StreamCatch media downloader.

## Table of Contents
1. [Architecture](#architecture)
2. [Core Components](#core-components)
3. [Advanced Features](#advanced-features)
4. [Troubleshooting](#troubleshooting)

---

## Architecture

StreamCatch uses a modular architecture to ensure robustness and maintainability.

### Frontend
- **Framework**: Flet (based on Flutter).
- **Design System**: Material Design 3.
- **Platform**: Windows, macOS, Linux, Web, iOS, Android.
- **State Management**: `AppState` singleton with observable properties.

### Backend
- **Downloader Engine**: `yt-dlp` for video extraction, `requests` for generic file downloads.
- **Queue Management**: `QueueManager` provides atomic, thread-safe operations for managing concurrent downloads.
- **Storage**: SQLite via `HistoryManager` for persistent history; JSON for configuration.

### Pipeline
1.  **Input**: URL from user or Clipboard Monitor.
2.  **Validation**: `ui_utils.validate_url`.
3.  **Info Extraction**: `downloader.get_video_info` (tries `yt-dlp` -> `TelegramExtractor` -> `GenericExtractor`).
4.  **Queuing**: Item added to `QueueManager`.
5.  **Processing**: Background thread claims item via `claim_next_downloadable()`.
6.  **Downloading**: `downloader.download_video` executes the download with progress hooks.
7.  **Post-Processing**: FFmpeg (conversion, metadata, thumbnail).
8.  **Completion**: History updated, notification sent.

---

## Core Components

### Downloader Module (`downloader.py`)
The heart of the application. It wraps `yt-dlp` but adds a robust layer of error handling and fallback mechanisms.
- **Robustness**: If `yt-dlp` fails to identify a URL (e.g., a direct file link served with `content-disposition`), it falls back to `GenericExtractor`.
- **Telegram**: A custom `TelegramExtractor` scrapes public Telegram channels for video/image content.

### Queue Manager (`queue_manager.py`)
Handles the download queue.
- **Thread Safety**: All operations are locked.
- **Atomic Claiming**: The `claim_next_downloadable()` method prevents race conditions where multiple worker threads might try to download the same file.

### Generic Downloader (`generic_downloader.py`)
A specialized module for non-video sites.
- **Streaming**: Downloads large files in chunks to keep memory usage low.
- **Resumability**: (Future plan) Can be extended to support `Range` headers.

---

## Advanced Features

### Force Generic Mode
Sometimes, `yt-dlp` might try to interpret a direct file link (like `.mp4` from a CDN) as a webpage and fail. "Force Generic" bypasses the extraction logic and treats the URL as a direct download source.

### Time Range Downloading
StreamCatch allows downloading only a portion of a video.
- **Implementation**: Uses `yt-dlp`'s `download_ranges` with FFmpeg cutting.
- **Format**: `HH:MM:SS` (e.g., `00:01:30` to `00:02:00`).

### GPU Acceleration
Users can select `cuda` (NVIDIA), `vulkan` (AMD/Intel), or `auto` to speed up video recoding. This passes the appropriate flags to FFmpeg.

### Proxy & Privacy
Support for HTTP/HTTPS/SOCKS proxies to bypass geo-restrictions. Browser cookies can also be imported to access age-restricted content.

---

## Troubleshooting

### "FFmpeg not found"
Ensure FFmpeg is installed and in your system PATH. StreamCatch requires it for merging video/audio and format conversion.

### "Download Error"
- Check your internet connection.
- Verify the URL works in a browser.
- Try "Force Generic" if it's a direct file link.
- Update the application to get the latest `yt-dlp` core.

### Visual Glitches
If the UI looks incorrect, ensure you are not using a custom scaling factor that interferes with Flet/Flutter rendering.
