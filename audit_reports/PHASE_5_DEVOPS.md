# Audit Report: Phase 5 - DevOps, Build & Distribution

## Status: 📅 Planned

**Goal:** Establish automated, reproducible, and optimized build pipelines for all target platforms.

## 5.1 Desktop Build (Nuitka)
**Objective:** Create standalone, high-performance executables for Windows, Linux, and macOS.

*   **Tool:** Nuitka (Python Compiler).
*   **Script:** `scripts/build_installer.py`.
*   **Configuration:**
    *   `--standalone`: Bundles the Python interpreter and dependencies.
    *   `--onefile`: (Optional) creates a single binary (easier distribution but slower startup). Recommended to keep as folder for `installers` or use `--onefile` for portable releases.
    *   `--enable-plugin=tk-inter`: Essential for `filedialog` compatibility if Flet falls back to Tkinter dialogs.
    *   `--include-data-dir=assets=assets`: Ensures icons and images are bundled.
    *   `--include-data-dir=locales=locales`: Bundles translation files.
    *   `--windows-icon-from-ico=assets/icon.ico`: Sets the executable icon.
    *   `--nofollow-import-to=yt_dlp.extractor.lazy_extractors`: **Critical Optimization.** Prevents Nuitka from compiling thousands of lazy extractors, which bloats the binary and build time.
    *   `--lto=no`: Disable Link Time Optimization for faster builds during dev; enable for release.
*   **Action:** Update the build script to automatically detect the OS and apply relevant flags (e.g., `.ico` for Windows, `.icns` for Mac).

## 5.2 Mobile Build (Flutter/Flet)
**Objective:** Compile the Python Flet app into native Android (APK) and iOS (IPA) packages.

*   **Workflow:** `.github/workflows/build-mobile-flet.yml`.
*   **Android:**
    *   **Environment:** Ubuntu Latest, Java 17, Flutter 3.22.0+.
    *   **Command:** `flet build apk --build-number ${{ github.run_number }}`.
    *   **Signing:** Use GitHub Secrets (`ANDROID_KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_ALIAS`) to sign the APK for release.
*   **iOS:**
    *   **Environment:** `macos-latest` (runs on Mac hardware).
    *   **Command:** `flet build ipa`.
    *   **Signing:** Requires Apple Developer Account certificates and provisioning profiles stored in GitHub Secrets.

## 5.3 Installer (Windows)
**Objective:** Create a professional Windows installer.

*   **Tool:** Inno Setup 6.
*   **Script:** `installers/setup.iss`.
*   **Features:**
    *   **Wizard:** Welcome, License, Install Dir, Shortcuts.
    *   **Registry:** Register `streamcatch://` protocol to allow opening links directly into the app (optional).
    *   **Context Menu:** Add "Open with StreamCatch" to context menu (optional).
    *   **Uninstaller:** Clean removal of files.

## 5.4 Containerization
**Objective:** Provide a Docker image for headless or server-based usage.

*   **Dockerfile:**
    *   **Multi-stage Build:**
        *   *Stage 1 (Builder):* Install build deps, compile dependencies.
        *   *Stage 2 (Runtime):* `python:3.11-slim`, copy artifacts.
    *   **Volume Mounts:** Ensure `/config` and `/downloads` are exposed volumes.
*   **Docker Compose:**
    *   `docker-compose.yml` pre-configured with volume mappings and environment variables (`PUID`, `PGID` for permission management).
