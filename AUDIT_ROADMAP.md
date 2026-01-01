# Master Development Roadmap: StreamCatch 2.0 (Ultimate Edition)

This document serves as the **Definitive Execution Plan** for the StreamCatch project. It outlines the exhaustive steps required to transform the application into a production-grade, cross-platform media downloader.

**Current Version:** 2.0.0-dev
**Target Platforms:** Windows 10/11 (EXE), Android 10+ (APK), Linux (Binary/Deb), macOS (DMG/App).

---

## Phase 1: Foundation & Integrity (Completed)
**Status:** ✅ **Done**
**Goal:** Establish a rock-solid, type-safe, and thread-safe foundation.

*   **1.1 Strict Typing & Static Analysis**
    *   [x] **Action:** Enforce `strict=True` in `mypy.ini` for `downloader/`, `utils.py`, `ui_utils.py`, `app_controller.py`.
    *   [x] **Deliverable:** `downloader/types.py` defining `QueueItem`, `DownloadOptions`, `DownloadResult` TypedDicts/Dataclasses.
    *   [x] **Verification:** `mypy .` returns zero errors.
*   **1.2 Core Logic Hardening**
    *   [x] **Target:** `GenericDownloader` in `downloader/engines/generic.py`.
    *   [x] **Impl:** Added RFC 5987 filename parsing (`filename*=UTF-8''...`).
    *   [x] **Impl:** Implemented strict `_verify_path_security` to prevent `../` traversal.
    *   [x] **Target:** `downloader/core.py`. Added `_sanitize_output_path` with permission checks.
*   **1.3 Thread Safety**
    *   [x] **Target:** `QueueManager`. Switched to `threading.RLock` and `threading.Condition` for `wait_for_work`.
    *   [x] **Target:** `AppState`. Implemented thread-safe Singleton with `_init_lock`.
    *   [x] **Target:** `tasks.py`. Implemented `CancelToken` logic for granular task interruption.
*   **1.4 Robustness**
    *   [x] **Signal Handling:** Added `SIGINT`/`SIGTERM` handlers in `main.py`.
    *   [x] **Crash Reporting:** Enhanced `global_crash_handler` to sanitize and dump local variables.

---

## Phase 2: Core Architecture 2.0 (In Progress)
**Status:** 🚧 **In Progress**
**Goal:** Enhance data persistence, network resilience, and security.

*   **2.1 Advanced Data Management (Completed)**
    *   [x] **ConfigManager:** Added `_validate_schema` with strict type map (`use_aria2c: bool`, `gpu_accel: str`).
    *   [x] **HistoryManager:** Enabled `PRAGMA journal_mode=WAL` for concurrent SQLite access.
    *   [x] **Maintenance:** Added `vacuum()` method to `HistoryManager`.
*   **2.2 Network Engine Refinement (Partially Completed)**
    *   [x] **RateLimiter:** Rewrote `rate_limiter.py` using `TokenBucket` algorithm (Rate + Capacity).
    *   [ ] **BatchImporter Refactoring:**
        *   **File:** `batch_importer.py`.
        *   **Task:** Implement `async` verification of URLs (HEAD request) before adding to queue.
        *   **Spec:** `verify_url(url, timeout=3) -> bool`. Use `concurrent.futures`.
    *   [ ] **SocialManager Hardening:**
        *   **File:** `social_manager.py`.
        *   **Task:** Wrap `pypresence` calls in `try/except` with a circuit breaker (disable after 3 failures).
    *   [ ] **ClipboardMonitor Optimization:**
        *   **File:** `clipboard_monitor.py`.
        *   **Task:** Reduce polling rate if idle; implement OS-specific listeners (if feasible via `pyperclip` alternatives) or adaptive polling.
*   **2.3 Security Hardening (Pending Verification)**
    *   [ ] **SSRF Protection:**
        *   **File:** `ui_utils.py`.
        *   **Task:** Update `validate_url` to use `ipaddress` module.
        *   **Spec:** Block `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16` and IPv6 equivalents.
    *   [ ] **Cookie Encryption:**
        *   **File:** `config_manager.py`.
        *   **Task:** Encrypt `cookies` field using a machine-specific key (if `cryptography` lib is allowed) or simple obfuscation if not.

---

## Phase 3: Frontend & UX Revolution
**Status:** 📅 **Planned**
**Goal:** Migrate to a cohesive, responsive Material 3 Design System using Flet.

*   **3.1 Material 3 Design System (`theme.py`)**
    *   **Palette:** Define a `StreamCatchTheme` class inheriting from `ft.Theme`.
        *   **Primary:** `#6750A4` (Deep Purple).
        *   **Secondary:** `#625B71`.
        *   **Tertiary:** `#7D5260`.
        *   **Error:** `#B3261E`.
    *   **Typography:** Explicitly set `ft.TextTheme` attributes:
        *   `headline_large`: Roboto, 32sp, w400.
        *   `body_medium`: Roboto, 14sp, w400.
*   **3.2 Component Library (`views/components/`)**
    *   **`DownloadInputCard` (Modernization):**
        *   **Layout:** Use `ft.ResponsiveRow` for better mobile/desktop scaling.
        *   **Action:** Add `ft.FloatingActionButton(icon=ft.icons.PASTE, on_click=paste_and_go)`.
        *   **Chips:** Add `ft.Chip(label="Audio Only")`, `ft.Chip(label="Playlist")` toggles.
    *   **`DownloadItemControl` (Refactor):**
        *   **Visuals:** Replace text progress with `ft.ProgressBar(color=ft.colors.PRIMARY, height=8)`.
        *   **Metadata:** Use `ft.Badge` for "4K", "HDR".
        *   **Graph:** (Optional) Add `ft.LineChart` sparkline for speed history (last 30s).
    *   **`OptionsPanel` (Unification):**
        *   Create `views/components/panels/options_panel.py`.
        *   **Method:** `build_options(url_type: str) -> ft.Column`.
        *   Dynamically insert `YouTubePanel` or `InstagramPanel` logic.
*   **3.3 View Modernization**
    *   **`DashboardView`:**
        *   **Storage Widget:** `ft.PieChart` sections: "Free", "StreamCatch Downloads", "Other Used".
        *   **Activity Widget:** `ft.BarChart` showing "Downloads per Day" (query `HistoryManager`).
    *   **`QueueView`:**
        *   **Performance:** Implement "Windowing" manually if list > 100 items (render only visible + buffer).
        *   **Mobile:** Add `ft.Dismissible` for swipe-to-delete.
    *   **`SettingsView`:**
        *   **Layout:** Use `ft.ExpansionPanelList` for categories: "Network", "Storage", "Appearance", "System".
*   **3.4 Responsive Layout (`app_layout.py`)**
    *   **Logic:** Listen to `page.on_resized`.
    *   **Breakpoints:**
        *   **Width < 600px:** `ft.NavigationBar` (Bottom), `ft.AppBar` (Top).
        *   **Width 600-1200px:** `ft.NavigationRail` (Left, extended=False).
        *   **Width > 1200px:** `ft.NavigationRail` (Left, extended=True).

---

## Phase 4: Quality Assurance & Test Engineering
**Status:** 📅 **Planned**
**Goal:** Achieve >90% coverage and ensure regression-free releases.

*   **4.1 Unit Testing (`tests/unit/`)**
    *   **Target:** `batch_importer.py`.
        *   **Test:** `test_parse_txt`, `test_parse_csv`, `test_parse_invalid`.
    *   **Target:** `social_manager.py`.
        *   **Test:** `test_connect_timeout`, `test_update_activity`.
*   **4.2 Integration Testing (`tests/integration/`)**
    *   **`test_full_lifecycle.py`:**
        *   **Scenario:** `AppController.on_add_to_queue(url)` -> `QueueManager` (Queued) -> `Task` (Downloading) -> `HistoryManager` (Saved).
    *   **`test_persistence.py`:**
        *   **Scenario:** Add items -> `AppState.save()` -> Reload `AppState` -> Verify items exist.
*   **4.3 UI Testing**
    *   **Headless:** Create `MockPage` that implements `add`, `update`, `clean`.
    *   **Scenario:** Drive `AppController` methods and assert `MockPage.controls` state.

---

## Phase 5: DevOps, Build & Distribution
**Status:** 📅 **Planned**
**Goal:** Automated, reproducible builds for all platforms.

*   **5.1 Desktop Build (Nuitka)**
    *   **File:** `scripts/build_installer.py`.
    *   **Flags:**
        *   `--standalone`: Bundle Python.
        *   `--onefile`: (Optional for Linux/Mac).
        *   `--enable-plugin=tk-inter`: Required for some file pickers if Flet falls back.
        *   `--include-data-dir=assets=assets`: Bundle icons/images.
        *   `--include-data-dir=locales=locales`: Bundle translations.
        *   `--windows-icon-from-ico=assets/icon.ico`.
        *   `--nofollow-import-to=yt_dlp.extractor.lazy_extractors`: Optimization.
    *   **Optimization:** Use `--lto=no` (Link Time Optimization disabled for faster build) or `yes` for smaller size.
*   **5.2 Mobile Build (Flutter/Flet)**
    *   **Workflow:** `.github/workflows/build-mobile-flet.yml`.
    *   **Android:**
        *   **Env:** `JAVA_VERSION=17`, `FLUTTER_VERSION=3.22.0`.
        *   **Build:** `flet build apk --build-number ${{ github.run_number }}`.
        *   **Signing:** Decode `ANDROID_KEYSTORE_BASE64` to `upload-keystore.jks`.
    *   **iOS:**
        *   **Env:** `macos-latest`.
        *   **Build:** `flet build ipa`.
*   **5.3 Installer (Windows)**
    *   **Tool:** Inno Setup 6.
    *   **Script:** `installers/setup.iss`.
    *   **Features:**
        *   Associate `.url`? No.
        *   Register `streamcatch://` protocol.
        *   "Add to PATH" checkbox.
*   **5.4 Containerization**
    *   **Docker:** Update `Dockerfile` to use multi-stage build (Builder -> Runtime) for smaller image size.
    *   **Compose:** Verify `docker-compose.yml` mounts volumes correctly for `config` and `downloads`.

---

## Phase 6: Documentation & Knowledge Base
**Status:** 📅 **Planned**
**Goal:** Professional-grade documentation.

*   **6.1 User Wiki (`wiki/`)**
    *   **Page:** `Installation.md` (Windows, Android, Linux).
    *   **Page:** `Features.md` (Detailed breakdown of formats, scheduling).
    *   **Page:** `Troubleshooting.md` (FFmpeg missing, Network errors).
*   **6.2 Developer Guide (`project_docs/`)**
    *   **Content:**
        *   "Setting up Dev Env" (Pip, PDM, or Poetry).
        *   "Running Tests".
        *   "Building for Production".
        *   "Architecture Overview" (Mermaid diagrams).

---

## Phase 7: Final Polish & Release
**Status:** 📅 **Planned**
**Goal:** Release v2.0.0.

*   **7.1 Code Cleanup**
    *   **Action:** Delete `tasks_extended.py` (merged logic into `tasks.py`).
    *   **Action:** Run `pylint --rcfile=.pylintrc .` and achieve score > 9.5.
*   **7.2 Verification**
    *   **Manual QA:**
        *   **Windows:** Install via Inno Setup, run, download YouTube video.
        *   **Android:** Install APK, grant permissions, download.
*   **7.3 Launch**
    *   **Tag:** `git tag v2.0.0`.
    *   **Release:** Push to GitHub.
    *   **Announce:** Update `README.md` with new screenshots and badges.

---

**Definition of Done (DoD) for Project:**
1.  All P0/P1 bugs resolved.
2.  Test coverage > 85%.
3.  Successful build artifacts for Windows (EXE) and Android (APK).
4.  Documentation complete and reviewed.
