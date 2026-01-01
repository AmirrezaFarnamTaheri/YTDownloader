# Audit Report: Phase 5 - DevOps, Build & Distribution

## Status: 📅 Planned

**Goal:** Establish automated, reproducible, and optimized build pipelines for all target platforms.

## 5.1 Desktop Build (Nuitka)
**Objective:** Create standalone, high-performance executables.

*   **Script Analysis (`scripts/build_installer.py`):**
    *   **Env Var:** Sets `YTDLP_NO_LAZY_EXTRACTORS=1`. **Critical:** This prevents Nuitka from trying to compile ~100k lines of lazy extractor code, which would crash the compiler or produce a massive binary.
    *   **Flags:**
        *   `--standalone`: Bundles Python shared libs.
        *   `--nofollow-import-to=yt_dlp.extractor.lazy_extractors`: Explicitly excludes lazy extractors from compilation (they are imported dynamically).
        *   `--include-package=pypresence`: Forces inclusion of libraries that Nuitka might miss due to dynamic imports.
    *   **OS Specifics:**
        *   **Windows:** Embeds `.ico`, sets FileVersion/ProductVersion resource strings.
        *   **macOS:** Creates `.app` bundle structure (`Contents/MacOS`, `Contents/Resources`).
*   **Action Items:**
    *   Enable `--lto=yes` (Link Time Optimization) for release builds to reduce binary size (currently commented out).
    *   Add `--enable-plugin=tk-inter` if any file dialogs fall back to Tkinter.

## 5.2 Mobile Build (Flutter/Flet)
**Objective:** Compile for Android and iOS.

*   **Workflow (`.github/workflows/build-mobile-flet.yml`):**
    *   **Android:**
        *   Uses `ubuntu-latest`.
        *   Installs Java 17, Flutter 3.x.
        *   Command: `flet build apk`.
        *   Artifact: `build/apk/app-release.apk`.
    *   **iOS:**
        *   Uses `macos-latest`.
        *   Command: `flet build ipa`.
        *   **Constraint:** Requires valid Apple Developer Certificate and Provisioning Profile (P12/MobileProvision) in GitHub Secrets. Without these, the build will fail or produce an unsigned `.runner` app.

## 5.3 Distribution
**Objective:** Packaging for end-users.

*   **Windows:**
    *   **Tool:** Inno Setup 6 (`ISCC.exe`).
    *   **Script:** `installers/setup.iss`.
    *   **Output:** `StreamCatch_Setup_v2.0.0.exe`.
*   **Linux:**
    *   **Format:** `.deb` (Debian/Ubuntu).
    *   **Tools:** `fakeroot`, `dpkg-deb`.
    *   **Structure:** `/usr/local/bin/streamcatch`, `/usr/share/applications/streamcatch.desktop`.
*   **macOS:**
    *   **Format:** `.dmg` (Disk Image).
    *   **Tool:** `hdiutil`.
    *   **Content:** Contains `StreamCatch.app` and a symlink to `/Applications`.

## 5.4 Containerization
**Objective:** Server/Headless deployment.

*   **Dockerfile:**
    *   **Base:** `python:3.12-slim`.
    *   **Dependencies:** `ffmpeg` (pinned version), `aria2`.
    *   **Security:** Runs as non-root user `streamcatch` (UID 1000).
    *   **Volumes:**
        *   `/app/downloads`: Download target.
        *   `/home/streamcatch/.streamcatch`: Config/DB storage.
    *   **Env:** `FLET_WEB=1`, `FLET_SERVER_PORT=8550`.
*   **Docker Compose:**
    *   Orchestrates the container with volume mappings.
