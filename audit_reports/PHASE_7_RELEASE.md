# Audit Report: Phase 7 - Final Polish & Release

## Status: 📅 Planned

**Goal:** Ensure the application is polished, bug-free, and ready for public launch (v2.0.0).

## 7.1 Code Cleanup
**Objective:** Eliminate technical debt.

*   **Refactoring:**
    *   **Action:** Verify if `tasks_extended.py` is still needed. If logic is duplicated in `tasks.py`, delete it.
    *   **Imports:** Run `isort .` to ensure standard sorting (Stdlib -> Third Party -> Local).
    *   **Linting:**
        *   Run `pylint --rcfile=.pylintrc .`.
        *   Address all `E` (Error) and `W` (Warning) codes.
        *   Ensure `R` (Refactor) scores are acceptable (> 9.0).
*   **Security Audit:**
    *   Scan for hardcoded secrets (API keys, tokens).
    *   Verify `debug` flags are `False` by default.

## 7.2 Release Checklist
**Objective:** Granular steps for the release manager.

1.  **Version Bump:**
    *   Update `__version__` in `main.py`.
    *   Update `version` in `pyproject.toml` (if exists).
2.  **Changelog:**
    *   Update `CHANGELOG.md` with all features (Material 3, Thread Safety, WAL Mode) and fixes.
3.  **Manual QA (Staging):**
    *   **Windows:** Install `StreamCatch_Setup_v2.0.0-rc1.exe`. Test clean install and upgrade.
    *   **Android:** Install APK on physical device. Test Background downloading.
    *   **Linux:** Install `.deb`. Test `ffmpeg` detection.
4.  **Tagging:**
    *   `git tag -a v2.0.0 -m "Release v2.0.0"`
    *   `git push origin v2.0.0`
5.  **GitHub Release:**
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
