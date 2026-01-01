# Audit Report: Phase 3 - Frontend & UX Revolution

## Status: 📅 Planned / 🚧 Partial

**Goal:** Migrate the application to a cohesive, responsive Material 3 Design System using Flet, improving user experience and visual consistency.

## 3.1 Material 3 Design System (`theme.py`)
**Status:** **Verified**
*   **Implementation:**
    *   **Theme Class:** "Soulful Palette V3" is implemented with distinct colors (`PRIMARY`, `ACCENT`, `BG_DARK`).
    *   **Definitions:** Subclasses (`Surface`, `Primary`, `Status`) provide semantic access to colors.
    *   **Decorators:** `get_input_decoration` and `get_card_decoration` standardize UI components.
    *   **High Contrast:** `get_high_contrast_theme` implements a compliant high-contrast mode (Black/Yellow/White).
    *   **Gap:** `ft.TextTheme` is not explicitly defined in `get_theme()`, relying on Flet defaults.
    *   **Recommendation:** Explicitly define `text_theme` in `get_theme` to enforce Roboto font weights and sizes across the app.

## 3.2 Component Library (`views/components/`)
**Status:** **Partial / Verified**
*   **`DownloadInputCard` (in `DownloadView`):**
    *   *Analysis:* Not a standalone component; implemented directly in `DownloadView`.
    *   *Features:* Has responsive layout (`ft.Row` wrapping), URL input with paste button, and advanced options expansion.
    *   *Refactor:* Should be extracted to `views/components/download_input_card.py` to reduce `DownloadView` complexity.
*   **`DownloadItemControl` (`views/components/download_item.py`):**
    *   *Analysis:* Standalone class. Uses `ft.Container` with card styling.
    *   *Features:* Visual progress bar, status badges (Allocating, Downloading, etc.), and context-aware action buttons (Play, Cancel, Retry).
    *   *Memory:* Uses `weakref` for `item["control_ref"]` to prevent memory leaks.
    *   *Responsiveness:* Good. Uses `ft.Column` within the main row to stack title/status on smaller screens (implied by layout).
*   **`OptionsPanel` (`views/components/panels/`):**
    *   *Analysis:* Implemented via Factory Pattern logic in `DownloadView.update_video_info`.
    *   *Panels:* `YouTubePanel`, `InstagramPanel`, `GenericPanel` exist.
    *   *Refactor:* Formalize the factory into `PanelFactory` class to clean up `DownloadView`.

## 3.3 View Modernization
**Status:** **Partial**
*   **`DownloadView` (`views/download_view.py`):**
    *   *Layout:* Uses `ft.Column` with `scroll=ft.ScrollMode.AUTO`. Good structure.
    *   *Inputs:* `TextField` and `Dropdown` use standardized decorations from `Theme`.
    *   *Responsiveness:* Uses `wrap=True` in Header row. Footer logic checks `sys.platform`.
*   **`QueueView` (`views/queue_view.py`):**
    *   *Virtualization:* Implements standard `ft.ListView`. For large queues (>1000 items), Flet's default list view might stutter. Currently no manual windowing logic found.
    *   *State:* `rebuild()` clears and re-adds all controls. This is inefficient for frequent progress updates. However, `DownloadItemControl` handles its own `update_progress` internally, which mitigates this.
    *   *Bulk Actions:* "Cancel All" and "Clear Completed" buttons implemented and enabled/disabled dynamically based on queue state.
    *   *Navigation:* Implements keyboard navigation (`J`/`K`) via `select_item`, updating border/shadow for focus indication.
*   **`SettingsView` (`views/settings_view.py`):**
    *   *Feedback:* Validates inputs (path, proxy, regex) and shows `SnackBar` errors immediately on save.
    *   *State:* Auto-saves theme mode changes immediately. Other settings saved on button click.
    *   *Layout:* Sections (General, Network, Appearance) clearly separated by card containers.

## 3.4 Identified Gaps & Recommendations
*   **Automatic Responsiveness:** `AppLayout` needs a listener for page resize events to automatically collapse the sidebar or switch to a bottom navigation bar on mobile widths (< 600px).
*   **Component Extraction:** Extract the input section of `DownloadView` into a reusable `DownloadInputCard` component.
*   **Text Theme:** Explicitly define typography styles in `theme.py` to ensure consistency.
*   **Queue Performance:** For >100 items, `rebuild()` in `QueueView` is costly. Optimization: Only add/remove/update diffs instead of full clear, or use `ft.Column` with custom lazy loading if `ListView` proves insufficient.
