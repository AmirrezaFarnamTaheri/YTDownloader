# YTDownloader Wiki

## 📖 User Guide

### Getting Started
1.  **Installation:**
    *   **Windows:** Download and run `YTDownloader.exe`.
    *   **Linux/Mac:** Clone the repo and run `install-and-run.sh`.
2.  **Basic Usage:**
    *   Paste a YouTube link into the "URL" field.
    *   Click **Fetch Info**.
    *   Select your desired Video/Audio format from the tabs.
    *   Click **Add to Queue**.

### Advanced Features
*   **Playlists:** Check "Download entire playlist" to queue all videos found in the link.
*   **Subtitles:** Select a language in the "Subtitles" tab. "Auto" indicates auto-generated captions.
*   **Cookies:** Use the "Cookies" tab to bypass age restrictions by borrowing cookies from your browser.
*   **Proxy:** Configure a proxy in the "Settings" tab if you are in a restricted network environment.

---

## 💻 Developer Guide

### Project Structure
*   `main.py`: Entry point and GUI logic (Tkinter).
*   `downloader.py`: Wrapper around `yt-dlp`.
*   `config_manager.py`: Handles loading/saving JSON configuration.
*   `ui_utils.py`: Shared helper functions and constants.
*   `mobile/`: Kivy-based mobile application source.
*   `tests/`: Unit tests.

### Setting Up Development Environment
1.  Clone the repository.
2.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running Tests
Run the full test suite:
```bash
python -m unittest discover tests
```
For GUI tests in a headless environment (CI/Linux):
```bash
xvfb-run python -m unittest discover tests
```

### Building Executable
To build the Windows EXE:
```bash
pyinstaller ytdownloader.spec
```
The output will be in `dist/YTDownloader.exe`.

### Building APK
Navigate to `mobile/` and run:
```bash
buildozer android debug
```
