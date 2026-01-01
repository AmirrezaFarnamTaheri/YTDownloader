# Audit Report: Phase 3 - Frontend & UX Revolution

## Status: 📅 Planned

**Goal:** Migrate the application to a cohesive, responsive Material 3 Design System using Flet, improving user experience and visual consistency.

## 3.1 Material 3 Design System (`theme.py`)
**Objective:** Establish a unified design language.

*   **Implementation Plan:**
    *   **Theme Class:** Create a `StreamCatchTheme` class inheriting from or configuring `ft.Theme`.
    *   **Color Palette (Soulful Palette V3):**
        *   **Primary:** `#6750A4` (Deep Purple) - Action buttons, active states.
        *   **Secondary:** `#625B71` - Secondary actions, less prominent UI elements.
        *   **Tertiary:** `#7D5260` - Accents, special highlights.
        *   **Error:** `#B3261E` - Error messages, delete actions.
        *   **Surface:** `#1C1B1F` (Dark) / `#FFFBFE` (Light) - Backgrounds.
    *   **Typography:**
        *   Define `ft.TextTheme` with consistent sizing.
        *   `headline_large`: Roboto, 32sp, w400 (Page Titles).
        *   `body_medium`: Roboto, 14sp, w400 (Standard Text).
        *   `label_small`: Roboto, 11sp, w500 (Captions, Badges).
    *   **Components:**
        *   Standardize `ft.Card` elevation and shape.
        *   Standardize `ft.TextField` border radius and padding.

## 3.2 Component Library (`views/components/`)
**Objective:** Create reusable, modular, and state-aware UI components.

*   **`DownloadInputCard` (Modernization):**
    *   **Current:** Simple text field.
    *   **Upgrade:**
        *   Wrap in `ft.Card` with proper padding.
        *   Use `ft.ResponsiveRow` to stack the input and button on mobile, but align them on desktop.
        *   **Features:**
            *   "Paste & Go" Floating Action Button (`ft.icons.PASTE`).
            *   Format Toggles: `ft.Chip` or `ft.SegmentedButton` for "Video", "Audio Only", "Playlist".
*   **`DownloadItemControl` (Refactor):**
    *   **Current:** Basic row with text status.
    *   **Upgrade:**
        *   **Visuals:** Replace text percentage with `ft.ProgressBar` (height=8, rounded).
        *   **Metadata:** Add `ft.Badge` or colored `ft.Container` for quality tags ("4K", "HDR", "60fps").
        *   **Interactive:** Add "Open Folder" and "Play" icon buttons directly on the item.
        *   **Graph (Optional):** Implement a sparkline using `ft.LineChart` to show download speed over the last 30 seconds.
*   **`OptionsPanel` (Unification):**
    *   **Problem:** Disparate panels for different extractors.
    *   **Solution:** Create a factory `views/components/panels/options_panel.py`.
    *   **API:** `build_options(url_type: str) -> ft.Column`.
    *   **Logic:** Dynamically load `YouTubePanel`, `InstagramPanel`, or `TwitterPanel` based on the URL detected in the input field.

## 3.3 View Modernization
**Objective:** Improve the layout and functionality of main application views.

*   **`DashboardView`:**
    *   **Widgets:**
        *   **Storage:** `ft.PieChart` showing "Free Space" vs "Used Space".
        *   **Activity:** `ft.BarChart` showing "Downloads" per day (requires `HistoryManager` aggregation query).
    *   **Quick Actions:** Large cards for "Batch Import", "Paste from Clipboard".
*   **`QueueView`:**
    *   **Performance:** If the queue exceeds 100 items, Flet's rendering may slow down. Implement "windowing" (virtualization) or pagination.
    *   **Mobile Experience:** Wrap items in `ft.Dismissible` to allow swipe-to-cancel or swipe-to-delete.
*   **`SettingsView`:**
    *   **Layout:** Move from a long scrolling list to an `ft.ExpansionPanelList` or `ft.Tabs`.
    *   **Categories:** Network (Proxy, Rate Limit), Storage (Paths, Temp), Appearance (Theme, Density), System (Updates, Reset).

## 3.4 Responsive Layout (`app_layout.py`)
**Objective:** Ensure the app works seamlessly on phones, tablets, and desktops.

*   **Strategy:** Listen to `page.on_resized` events.
*   **Breakpoints:**
    *   **Mobile (< 600px):**
        *   Navigation: `ft.NavigationBar` (Bottom).
        *   Layout: Single column, vertical stacking.
    *   **Tablet (600px - 1200px):**
        *   Navigation: `ft.NavigationRail` (Left, `extended=False` / Icon Only).
        *   Layout: Two-column grid where appropriate.
    *   **Desktop (> 1200px):**
        *   Navigation: `ft.NavigationRail` (Left, `extended=True` / Labels visible).
        *   Layout: Multi-column dashboard, side-by-side panels.
