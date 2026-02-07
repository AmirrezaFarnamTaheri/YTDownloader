# Troubleshooting Guide

This guide addresses common issues encountered when using StreamCatch.

## Installation Issues

### "Nuitka not found" during build
Ensure you have installed all dependencies:
```bash
pip install -r requirements-dev.txt
```
Nuitka is required to compile the application.

### "Flet binary not found"
If you are running from source, ensure `flet` is installed:
```bash
pip install flet==0.21.2
```
On the first run, Flet will download the necessary binaries. If you are offline, you must pre-download them.

## Runtime Issues

### "FFmpeg not found"
StreamCatch requires FFmpeg for merging video and audio formats.
*   **Windows**: Download FFmpeg and add it to your PATH, or place `ffmpeg.exe` and `ffprobe.exe` in the same directory as `StreamCatch.exe`.
*   **Linux**: `sudo apt install ffmpeg`
*   **macOS**: `brew install ffmpeg`

### Download Fails Immediately
*   **Check your internet connection.**
*   **Check the URL**: Ensure the URL is valid and accessible in a browser.
*   **Update**: Some sites change their layout frequently. StreamCatch relies on `yt-dlp`. If the internal `yt-dlp` is outdated (in the compiled build), you may need a newer version of StreamCatch.
*   **Cookies**: Some videos (age-gated, premium) require authentication. Use the "Browser Cookies" feature in the Download View to select your browser (e.g., Chrome, Firefox).

### "SponsorBlock" not working
SponsorBlock relies on a community database. If a video is new, segments might not be submitted yet. Ensure the "SponsorBlock" toggle is enabled in the settings.

## Performance

### UI is slow or unresponsive
*   If downloading many files (100+), the UI update overhead might be high.
*   Try "Compact Mode" in settings to reduce visual complexity.

### High Memory Usage
*   Downloading very large playlists or long streams can consume memory.
*   The application tries to stream data to disk, but some metadata processing happens in memory.

## Logs and Debugging

If the application crashes, a log file is usually created.
*   **Linux/macOS**: `~/.streamcatch/crash.log`
*   **Windows**: `%USERPROFILE%\.streamcatch\crash.log`

You can also run the application from a terminal to see real-time logs:
```bash
./StreamCatch
```


### Download Stuck at 0%
**Symptom**: The progress bar appears but does not move.
**Solution**:
1.  Check your internet connection.
2.  The site might be throttling requests. Try enabling "Force Generic" in advanced options.
3.  If using a Proxy, verify the settings in the Settings tab.


### "Sign In Required" (403 Forbidden)
**Symptom**: Download fails with an error indicating authentication is needed.
**Solution**:
1.  Go to the **Download** tab.
2.  Select your browser in the "Browser Cookies" dropdown.
3.  Ensure you are logged into the website in that browser.


### UI Glitches / Blank Screen
**Symptom**: The app opens but the window is blank or distorted.
**Solution**:
1.  Resize the window; this forces a redraw.
2.  If persistent, clear the configuration file:
    -   **Windows**: Delete `%USERPROFILE%\\.streamcatch\\config.json`
    -   **Linux**: Delete `~/.streamcatch/config.json`

## Reporting Bugs

If you encounter a bug not listed here:
1.  Open the application.
2.  Reproduce the error.
3.  Check the crash log: `~/.streamcatch/crash.log` (Linux/Mac) or `%USERPROFILE%\\.streamcatch\\crash.log` (Windows).
4.  Open an issue on GitHub with:
    -   Steps to reproduce.
    -   The crash log content.
    -   Your OS and App Version.