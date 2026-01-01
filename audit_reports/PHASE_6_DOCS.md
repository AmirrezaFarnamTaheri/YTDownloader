# Audit Report: Phase 6 - Documentation & Knowledge Base

## Status: 📅 Planned

**Goal:** Create professional-grade documentation to reduce support requests and aid development.

## 6.1 User Wiki (`wiki/`)
**Objective:** Comprehensive end-user guides.

*   **Structure:**
    *   **Installation.md:**
        *   **Windows:** Installer download link, step-by-step screenshots.
        *   **Android:** APK sideloading instructions ("Allow from unknown sources").
        *   **Linux:** `.deb` installation (`sudo dpkg -i ...`).
    *   **Features.md:**
        *   **Downloading:** Formats (Video/Audio), Quality selection.
        *   **Scheduling:** How to use the date/time picker.
        *   **Batch Import:** Spec for `.txt` files (one URL per line).
    *   **Troubleshooting.md:**
        *   "FFmpeg not found": How to install/link FFmpeg.
        *   "Network Error": Proxy settings, firewall.
        *   "Download Failed": Common `yt-dlp` errors (geo-block, age-gate) and solutions (Cookies, Proxy).

## 6.2 Developer Guide (`project_docs/`)
**Objective:** Onboarding and technical reference.

*   **DevEnvironment.md:**
    *   **Prerequisites:** Python 3.12, Git, FFmpeg.
    *   **Setup:**
        ```bash
        git clone https://github.com/.../StreamCatch.git
        python -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt -r requirements-dev.txt
        pre-commit install
        ```
*   **Architecture.md:**
    *   **Diagrams:** Mermaid charts showing:
        *   `AppController` -> `QueueManager` -> `Task (Thread)` -> `Downloader Engine`.
        *   `UI` -> `Controller` (Event Driven).
*   **ReleaseProcess.md:**
    *   Tagging strategy (`vX.Y.Z`).
    *   Monitoring GitHub Actions.
    *   Verifying artifacts.

## 6.3 API Reference
**Objective:** Document internal APIs.

*   While primarily a GUI app, documenting the `AppController` and `QueueManager` public methods allows for future CLI or API expansion.
*   **Key Classes:** `QueueManager`, `HistoryManager`, `GenericDownloader`.
