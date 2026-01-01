# Audit Report: Phase 7 - Final Polish & Release

## Status: 📅 Planned

**Goal:** Ensure the application is polished, bug-free, and ready for public launch (v2.0.0).

## 7.1 Code Cleanup
**Status:** **Pending**
*   **Refactoring:**
    *   **Action:** Verify if `tasks_extended.py` is still needed. If logic is duplicated in `tasks.py`, delete it.
    *   **Imports:** Run `isort .` to ensure standard sorting (Stdlib -> Third Party -> Local).
    *   **Linting:**
        *   Run `pylint --rcfile=.pylintrc .`.
        *   **Current Score:** **9.64/10** (Excellent).
        *   **Remaining Issues:**
            *   `E0401` (Import Error): `yt_dlp`, `requests`, `flet` not installed in analysis environment (False Positives in local context if env is minimal).
            *   `W0611` (Unused Import): `downloader.types.DownloadResult` in `core.py`.
            *   `R1705` (No Else Return): `history_manager.py`.
            *   `C0103` (Invalid Name): `_executor` in `tasks.py`.
*   **Security Audit:**
    *   Scan for hardcoded secrets (API keys, tokens).
    *   Verify `debug` flags are `False` by default in `main.py` (checked: `console_mode` depends on args).

## 7.2 Release Checklist
**Status:** **Pending**
*   **Version Bump:**
    *   `main.py`: Not explicitly defined as `__version__`.
    *   **Action:** Add `__version__ = "2.0.0"` to `main.py`.
    *   `pyproject.toml`: Verify version field.
*   **Changelog:**
    *   Update `CHANGELOG.md` with all features (Material 3, Thread Safety, WAL Mode) and fixes.
*   **Manual QA (Staging):**
    *   **Windows:** Install `StreamCatch_Setup_v2.0.0-rc1.exe`. Test clean install and upgrade.
    *   **Android:** Install APK on physical device. Test Background downloading.
    *   **Linux:** Install `.deb`. Test `ffmpeg` detection.
*   **Tagging:**
    *   `git tag -a v2.0.0 -m "Release v2.0.0"`
    *   `git push origin v2.0.0`
*   **GitHub Release:**
    *   Wait for Actions to complete.
    *   Verify artifacts (checksums).
    *   Publish Release.

## 7.3 Definition of Done (DoD)
**Criteria for Success:**
1.  **Zero Critical Bugs:** No crashes, data loss, or security vulnerabilities.
2.  **Test Coverage:** > 85% line coverage.
3.  **Build Success:** All artifacts (EXE, APK, DEB, DMG) built successfully in CI.
4.  **Documentation:** Wiki and Readme updated.
5.  **Performance:** App startup < 2s. Memory usage < 200MB (idle).
