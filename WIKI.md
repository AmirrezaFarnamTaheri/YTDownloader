# StreamCatch Wiki

## User Guide

### Basics
- **Download**: Paste a URL into the input box and click "Fetch Info". Review options and click "Add to Queue".
- **Queue**: Monitor progress. You can pause (cancel) or remove items. Use the arrows to reorder priority.
- **History**: View past downloads and open their folder.

### Advanced Features
- **Batch Import**: Click the upload icon in the header to import a `.txt` file containing a list of URLs (one per line).
- **Scheduling**: Click the clock icon to set a start time for the next added download.
- **Cookies**: Use the "Browser Cookies" dropdown to bypass age restrictions or access premium content (requires the browser to be installed and logged in).
- **SponsorBlock**: Check the box to automatically remove sponsored segments from YouTube videos.

## Technical Details

### Robustness & Reliability
StreamCatch is designed to be "theoretically robust", meaning it handles edge cases gracefully:
1.  **Atomic Queue Operations**: The `QueueManager` uses locks to prevent race conditions when multiple threads access the queue.
2.  **Fallback Pipeline**:
    -   Tries `yt-dlp` (standard).
    -   If `yt-dlp` fails, tries `GenericExtractor` (for direct files).
    -   Specific logic for Telegram (`t.me`) links.
3.  **State Recovery**: If the app crashes, the history DB is safe (WAL mode).

### Mobile Architecture
The mobile app (`mobile/`) is now deprecated in favor of the Flet unified codebase. `main.py` adapts its layout using `ResponsiveRow` and flexible containers to render correctly on mobile screens.

### Build Process
We use `pyinstaller` for Desktop and `flet build` for Mobile.
- **Desktop**: `pyinstaller streamcatch.spec`
- **Android**: `flet build apk`
