# User Guide

## Getting Started

### Installation
Please refer to the [Installation Page](Installation.md) for detailed instructions for your operating system (Windows, Linux, macOS).

### First Launch
Upon opening StreamCatch, you will see the main Dashboard. The interface is divided into several tabs:
*   **Download**: The main area for pasting URLs and starting downloads.
*   **Queue**: Manages active, pending, and completed downloads.
*   **History**: A persistent log of all your downloads.
*   **Settings**: Configure app behavior, appearance, and network settings.

## Downloading Media

### 1. Standard Download
1.  **Paste URL**: Copy a link from YouTube, Twitter, Instagram, TikTok, or Telegram. Paste it into the "Video URL" field on the **Download** tab.
2.  **Fetch Info**: Click the **Fetch Info** (Search) button. StreamCatch will retrieve metadata (Title, Duration, Formats).
3.  **Customize**:
    -   **Video Quality**: Choose from available resolutions (e.g., 1080p, 4k, 720p) or "Best".
    -   **Audio Format**: Extract audio only if desired.
    -   **Subtitles**: Select a language (e.g., `en`, `es`) to embed subtitles.
    -   **Time Range**: Specify Start/End times (e.g., `00:01:30` to `00:02:00`) to download a clip.
4.  **Queue It**: Click **Add to Queue**. The download starts automatically in the background.

### 2. Batch Import
Have a list of links?
1.  Create a `.txt` file with one URL per line.
2.  Click the **Batch Import** (Upload) icon in the Download tab header.
3.  Select your file. StreamCatch will queue all valid links instantly.

### 3. Scheduling
Plan downloads for later (e.g., off-peak hours):
1.  Click the **Schedule** (Clock) icon.
2.  Pick a time.
3.  The *next* item you add to the queue will be scheduled for that time.

### 4. Browser Cookies (Bypassing Restrictions)
Some content (Age-gated, Premium) requires authentication. StreamCatch can borrow cookies from your browser:
1.  In the **Download** tab, look for the "Browser Cookies" dropdown.
2.  Select your browser (e.g., Chrome, Firefox).
3.  StreamCatch will extract cookies from your local browser profile to authenticate the request.
    *   *Note: You must be logged in to the site in that browser, and you should only use this on devices and profiles you trust.*

## Queue Management
Navigate to the **Queue** tab to manage active tasks:
-   **Real-time Stats**: View download speed, ETA, and file size.
-   **Prioritize**: Use the Up/Down controls to move pending items up or down the list.
-   **Control**: Cancel active downloads or remove completed ones.
-   **Retry**: Failed downloads can be retried with a single click.

## Configuration
In the **Settings** tab, you can configure:
-   **Theme**: Toggle between Light, Dark, and System mode.
-   **Language**: Choose your preferred UI language (restart required for full refresh).
-   **Downloads Folder**: Set the default location for saved files.
-   **Output Template**: Customize how filenames are generated.
-   **Max Concurrent Downloads**: Limit how many files download at once.
-   **Proxy**: Configure a proxy server (HTTP/SOCKS) to bypass geo-restrictions.
-   **Rate Limit**: Set a speed limit (e.g., `5M`, `500K`) to prevent bandwidth saturation.
