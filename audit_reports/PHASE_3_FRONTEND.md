# Audit Report: Phase 3 - Frontend & UX Revolution

## Status: 📅 Planned

**Goal:** Migrate the application to a cohesive, responsive Material 3 Design System using Flet, improving user experience and visual consistency.

## 3.1 Material 3 Design System (`theme.py`)
**Objective:** Establish a unified design language based on the "Soulful Palette V3".

*   **Current State:**
    *   `Theme` class defines static colors: `PRIMARY = "#818CF8"` (Indigo 400), `ACCENT = "#F472B6"` (Pink 400).
    *   `get_theme()` returns a `ft.Theme` with `ft.ColorScheme` mapped to these constants.
    *   High Contrast mode is implemented (`get_high_contrast_theme`).
*   **Expansion Plan:**
    *   **Typography:** Define `ft.TextTheme` explicitly.
        *   `headline_large`: Roboto, 32sp, w400.
        *   `title_medium`: Roboto, 16sp, w500.
        *   `body_medium`: Roboto, 14sp, w400.
    *   **Component Defaults:**
        *   `ft.Card`: Elevation 2, Radius 12.
        *   `ft.FloatingActionButton`: Radius 16.

## 3.2 Component Library (`views/components/`)
**Objective:** Create reusable, modular, and state-aware UI components.

*   **`DownloadInputCard` (Modernization):**
    *   **Refactor:** Break into smaller sub-controls (`UrlInput`, `FormatSelector`).
    *   **Logic:**
        *   Validate URL on type (debounce 500ms).
        *   Show "Paste" FAB only when clipboard has valid URL (via signal).
*   **`DownloadItemControl` (Refactor):**
    *   **Visuals:**
        *   Replace text status with `ft.ProgressBar` (height=6, `border_radius=3`).
        *   Add `ft.Badge` for quality ("4K", "HD") and type ("Video", "Audio").
    *   **Interaction:**
        *   Hover effects: Show "Cancel", "Pause" buttons on hover (Desktop).
        *   Context Menu: Right-click for "Copy URL", "Show in Folder".
*   **`OptionsPanel` (Factory Pattern):**
    *   Create `views/components/panels/options_factory.py`.
    *   Returns `YouTubePanel` (cookies, subtitles), `InstagramPanel` (login), or `GenericPanel` based on URL regex.

## 3.3 View Modernization
**Objective:** Improve the layout and functionality of main application views.

*   **`DashboardView`:**
    *   **Widgets:**
        *   **Storage:** `ft.PieChart` (Free vs Used).
        *   **Network:** `ft.LineChart` (Download speed over time).
    *   **Layout:** Grid (Masonry) layout for widgets.
*   **`QueueView`:**
    *   **Performance:** Implement Virtualization. Flet's `ListView` handles some, but for >1000 items, custom windowing (rendering only visible + 20 buffer) is needed.
    *   **Mobile:** `ft.Dismissible` wrapper for swipe actions.
*   **`SettingsView`:**
    *   **Organization:** `ft.Tabs` for "General", "Network", "Appearance", "Advanced".
    *   **Validation:** Immediate feedback (red border) for invalid paths or proxies.

## 3.4 Responsive Layout (`app_layout.py`)
**Objective:** Ensure the app works seamlessly on phones, tablets, and desktops.

*   **Current State:** `main.py` sets `window_min_width = 1100`. This is too wide for mobile.
*   **New Logic:**
    *   Remove rigid `min_width`.
    *   **Breakpoint Observer:**
        *   **< 600px (Mobile):**
            *   Hide `NavigationRail`.
            *   Show `NavigationBar` (Bottom).
            *   Stack columns vertically.
        *   **600px - 1200px (Tablet):**
            *   Show `NavigationRail` (`extended=False`, icons only).
        *   **> 1200px (Desktop):**
            *   Show `NavigationRail` (`extended=True`, labels visible).
            *   Two-column layout for Dashboard (Stats | Recent).
