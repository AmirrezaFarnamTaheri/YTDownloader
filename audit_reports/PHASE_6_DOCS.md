# Audit Report: Phase 6 - Documentation & Knowledge Base

## Status: 📅 Planned

**Goal:** Create professional-grade documentation to reduce support requests and aid development.

## 6.1 User Wiki (`wiki/`)
**Objective:** Comprehensive end-user guides.

*   **Structure:**
    *   **Home:** Welcome, Quick Start.
    *   **Installation.md:**
        *   **Windows:** Installer download link, step-by-step screenshots.
        *   **Android:** APK sideloading instructions.
        *   **Linux:** Binary usage or DEB install.
    *   **Features.md:**
        *   **Downloading:** Formats (Video/Audio), Quality selection.
        *   **Scheduling:** How to use the date/time picker.
        *   **Batch Import:** CSV/TXT format specification.
    *   **Troubleshooting.md:**
        *   "FFmpeg not found": How to install/link FFmpeg.
        *   "Network Error": Proxy settings, firewall.
        *   "Download Failed": Common `yt-dlp` errors and solutions (e.g., update app).

## 6.2 Developer Guide (`project_docs/`)
**Objective:** Onboarding and technical reference for contributors.

*   **Setting up Dev Env:**
    *   `git clone ...`
    *   `python -m venv venv`
    *   `pip install -r requirements.txt -r requirements-dev.txt`
*   **Running Tests:**
    *   `pytest` usage.
    *   How to write new tests.
*   **Building for Production:**
    *   Running `scripts/build_installer.py`.
    *   Testing the build artifact.
*   **Architecture Overview:**
    *   **Mermaid Diagrams:**
        *   **Data Flow:** URL -> UI -> Controller -> Queue -> Engine -> Disk.
        *   **Class Diagram:** Relationships between `AppController`, `UIManager`, `Downloader`, and `AppState`.

## 6.3 API Documentation
**Objective:** Document internal APIs if providing a headless interface or plugins.

*   While primarily a GUI app, documenting the `AppController` public methods allows for future CLI or API expansion.
