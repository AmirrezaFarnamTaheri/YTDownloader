# Features

StreamCatch is packed with powerful features designed to make media downloading seamless and robust.

## 📥 Smart Downloading
*   **Universal Support**: Download from YouTube, Twitter/X, Instagram, TikTok, Twitch, and 1000+ other sites via `yt-dlp`.
*   **Generic File Downloader**: Download any file from a direct link (PDF, ISO, ZIP, etc.) with resume capability.
*   **Batch Import**: Import lists of URLs from `.txt` or `.csv` files. StreamCatch verifies links in parallel before queuing.
*   **Clipboard Monitor**: Automatically detects URLs copied to your clipboard and prompts to download.

## 🚀 Performance
*   **Multi-threaded Engine**: Uses a thread pool to handle concurrent downloads efficiently.
*   **Network Resilience**: Smart retry logic with exponential backoff for failed downloads.
*   **Rate Limiting**: Set global speed limits (e.g., `5M`, `500K`) to manage bandwidth.
*   **Aria2c Integration**: Optional integration with `aria2c` for accelerated downloading.

## 🎨 Modern UI
*   **Dashboard**: Visual overview of system storage, active tasks, and download activity history.
*   **Dark Mode**: Fully themed Material 3 dark mode by default, with Light and System options.
*   **Responsive Design**:
    *   **Desktop**: Sidebar navigation for efficient management.
    *   **Mobile**: Bottom navigation bar and optimized touch targets.
    *   **Compact Mode**: Automatically adjusts for smaller windows.

## 🛡️ Security & Privacy
*   **SSRF Protection**: Blocks downloads from private/local IP ranges to prevent server-side request forgery attacks.
*   **Config Encryption**: Sensitive data (like cookies) is obfuscated in the configuration file using a machine-specific key.
*   **Safe File Handling**: Filename sanitization and path traversal prevention.

## ⚙️ Advanced Control
*   **Scheduling**: Schedule downloads to start at a specific time.
*   **Browser Cookies**: Import cookies from Chrome/Firefox/Edge to access age-gated or premium content.
*   **Metadata Embedding**: Automatically embeds thumbnails, chapters, and metadata into files.
*   **Proxy Support**: Full HTTP/SOCKS proxy support for bypassing geo-restrictions.
