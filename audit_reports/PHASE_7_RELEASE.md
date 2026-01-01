# Audit Report: Phase 7 - Final Polish & Release

## Status: 📅 Planned

**Goal:** Ensure the application is polished, bug-free, and ready for public launch (v2.0.0).

## 7.1 Code Cleanup
**Objective:** Eliminate technical debt before release.

*   **Refactoring:**
    *   **Merge:** `tasks_extended.py` logic should be fully merged into `tasks.py` if not already done, or deleted if obsolete.
    *   **Imports:** Sort imports using `isort` and remove unused imports.
*   **Linting:**
    *   Run `pylint --rcfile=.pylintrc .`.
    *   Target score: > 9.5/10.
    *   Address all P0 (Error) and P1 (Warning) issues. Suppress only false positives with clear comments.

## 7.2 Verification
**Objective:** Final manual validation.

*   **Manual QA Checklist:**
    *   **Windows:**
        *   Install via generated `.exe`.
        *   Launch app.
        *   Download a YouTube video (1080p).
        *   Download an audio track (MP3).
        *   Verify metadata (Author, Title) in file properties.
    *   **Android:**
        *   Install APK.
        *   Grant Storage permissions.
        *   Share a URL from YouTube app to StreamCatch.
        *   Verify download completes.

## 7.3 Launch
**Objective:** executing the release strategy.

*   **Versioning:**
    *   Update `__version__` in `main.py` (or central version file).
    *   Create Git Tag: `git tag v2.0.0`.
    *   Push tag: `git push origin v2.0.0`.
*   **GitHub Release:**
    *   Draft new release from tag.
    *   Upload artifacts: `StreamCatch-Setup.exe`, `StreamCatch.apk`, `StreamCatch-Linux`.
    *   Release Notes: Highlight "Material Design 3", "Improved Speed", "Security Fixes".
*   **Announcement:**
    *   Update `README.md` with new screenshots, "Stable" badges, and download links.
