# Troubleshooting

## Common Issues

### "ffmpeg not found"
**Symptom**: Downloads start but fail during the "Merging" or "Converting" stage.
**Solution**:
-   **Windows**: The installer includes FFmpeg. If you are running from source, ensure `ffmpeg.exe` is in your PATH or the app directory.
-   **Linux**: Install via package manager: `sudo apt install ffmpeg`.
-   **macOS**: Install via Homebrew: `brew install ffmpeg`.

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
