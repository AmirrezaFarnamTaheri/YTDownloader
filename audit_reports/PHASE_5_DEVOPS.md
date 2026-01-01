# Audit Report: Phase 5 - DevOps, Build & Distribution

## Status: 📅 Planned / 🚧 In Progress

**Goal:** Establish automated, reproducible, and optimized build pipelines for all target platforms.

## 5.1 Desktop Build (Nuitka)
**Status:** **Verified**
*   **Script (`scripts/build_installer.py`):**
    *   **Optimization:** Sets `YTDLP_NO_LAZY_EXTRACTORS=1` via `os.environ` to prevent compiler exhaustion (critical for Windows).
    *   **Flags:**
        *   `--standalone`: Verified.
        *   `--nofollow-import-to=yt_dlp.extractor.lazy_extractors`: Verified.
        *   `--include-package`: Includes `pypresence`, `pydrive2`, `defusedxml` to handle hidden imports.
    *   **Packaging:**
        *   **macOS:** `ensure_macos_app_bundle` manually assembles the `.app` structure (Contents/MacOS, Resources, Info.plist) fixing Nuitka's standalone scatter.
        *   **Windows:** Integrates with Inno Setup (`ISCC.exe`) if present. Uses standardized version numbering (`X.X.X.X`).
*   **Gaps:**
    *   `--lto=yes` is commented out. Enabling it would reduce binary size but increase build time.
    *   `--onefile` is used for non-macOS, which increases startup time due to unpacking. A folder-based dist (just `--standalone`) might be better for an installer-based distribution.

## 5.2 Mobile Build (Flutter/Flet)
**Status:** **Verified**
*   **Workflow (`.github/workflows/build-mobile-flet.yml`):**
    *   **Android:**
        *   Uses `ubuntu-latest`, Java 17, Flutter 3.19.0.
        *   Runs `scripts/build_mobile.py --target apk`.
        *   Artifacts: Uploads `build/apk/*.apk`.
    *   **iOS:**
        *   Uses `macos-14` (Apple Silicon compatible).
        *   Runs `scripts/build_mobile.py --target ipa`.
        *   **Limitation:** Builds unsigned archive (`Runner.xcarchive`). Does not perform signing (requires certs/provisioning profiles in secrets).

## 5.3 Distribution & Containerization
**Status:** **Verified**
*   **Container Security (`Dockerfile`):**
    *   **User:** Runs as non-root user `streamcatch` (UID 1000). **Good.**
    *   **Base:** Uses `python:3.12-slim`. **Good.**
    *   **Dependencies:** Uses pinned versions for `ffmpeg` (7:5.1.6...), `aria2`, and `git` in `apt-get install` to ensure reproducibility.
    *   **Volumes:** Explicitly declares volumes for `/app/downloads` and `/home/streamcatch/.streamcatch`.
*   **Compose (`docker-compose.yml`):**
    *   **Mounts:** Correctly maps local `./downloads` and `./config` to the container's volume paths.
    *   **Ports:** Exposes 8550 for Flet Web.

## 5.4 Identified Gaps & Recommendations
*   **LTO Optimization:** Uncomment `--lto=yes` in `build_installer.py` for Release builds to optimize performance.
*   **iOS Signing:** Add a step to decode `IOS_CERTIFICATE_BASE64` and `IOS_PROVISIONING_PROFILE_BASE64` in the GitHub workflow if valid signing is required.
*   **Docker Healthcheck:** Add a `HEALTHCHECK` instruction to `Dockerfile` (e.g., `curl -f http://localhost:8550/ || exit 1`) to improve orchestration reliability.
