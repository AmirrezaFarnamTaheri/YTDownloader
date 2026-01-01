# Audit Report: Phase 6 - Documentation & Knowledge Base

## Status: 📅 Planned / 🚧 Partial

**Goal:** Create professional-grade documentation to reduce support requests and aid development.

## 6.1 User Wiki (`wiki/`)
**Status:** **Verified (Partial)**
*   **Existing Files:**
    *   `API.md`: Likely contains internal API docs.
    *   `Architecture.md`: High-level system design.
    *   `Concepts.md`: Explains core concepts (queue, tasks).
    *   `Troubleshooting.md`: Common issues.
*   **Gaps:**
    *   **Missing `Installation.md`:** Essential for new users. Needs to cover Windows (Installer), Linux (Binary/Deb), and Android (APK).
    *   **Missing `Features.md`:** Detailed breakdown of formats, scheduling, batch import, and browser cookies.

## 6.2 Developer Guide (`project_docs/`)
**Status:** **Verified**
*   **Existing Files:**
    *   `Developer-Guide.md`: Setup, testing, and contribution rules.
    *   `Installation.md`: (Likely for devs, checking if this covers users too).
    *   `User-Guide.md`: End-user manual.
*   **Assessment:**
    *   The split between `wiki/` and `project_docs/` is confusing. `project_docs/` seems to contain both user and dev docs.
    *   **Recommendation:** Consolidate. Move user-facing docs to `wiki/` (GitHub Wiki standard) and keep dev docs in `project_docs/` or `docs/`.

## 6.3 API Reference
**Status:** **Partial**
*   **Current:** `API.md` exists in `wiki/`.
*   **Need:** Ensure it covers the public methods of `QueueManager`, `HistoryManager`, and `AppController` for potential plugin developers or CLI usage.

## 6.4 Identified Gaps & Recommendations
*   **Consolidation:** Merge `project_docs/User-Guide.md` into `wiki/` pages (`Features.md`, `Usage.md`).
*   **Installation Guide:** Create a unified `wiki/Installation.md` with tabs/sections for each platform.
*   **Screenshots:** Documentation needs updated screenshots reflecting the new Material 3 UI.
