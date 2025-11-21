import flet as ft

class Theme:
    # Primary Colors
    PRIMARY = "#3B82F6"  # Blue 500
    PRIMARY_DARK = "#1D4ED8" # Blue 700
    ACCENT = "#8B5CF6"   # Violet 500

    # Backgrounds
    BG_DARK = "#0F172A"  # Slate 900
    BG_CARD = "#1E293B"  # Slate 800
    BG_HOVER = "#334155" # Slate 700

    # Text
    TEXT_PRIMARY = "#F8FAFC" # Slate 50
    TEXT_SECONDARY = "#94A3B8" # Slate 400

    # Status
    SUCCESS = "#10B981" # Emerald 500
    WARNING = "#F59E0B" # Amber 500
    ERROR = "#EF4444"   # Red 500

    # Borders
    BORDER = "#334155" # Slate 700

    @staticmethod
    def get_theme():
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=Theme.PRIMARY,
                secondary=Theme.ACCENT,
                background=Theme.BG_DARK,
                surface=Theme.BG_CARD,
                error=Theme.ERROR,
                on_primary=Theme.TEXT_PRIMARY,
                on_secondary=Theme.TEXT_PRIMARY,
                on_background=Theme.TEXT_PRIMARY,
                on_surface=Theme.TEXT_PRIMARY,
            ),
            visual_density=ft.VisualDensity.COMFORTABLE,
            page_transitions=ft.PageTransitionsTheme(
                android=ft.PageTransitionTheme.ZOOM,
                ios=ft.PageTransitionTheme.CUPERTINO,
                macos=ft.PageTransitionTheme.CUPERTINO,
                linux=ft.PageTransitionTheme.ZOOM,
                windows=ft.PageTransitionTheme.ZOOM,
            )
        )
