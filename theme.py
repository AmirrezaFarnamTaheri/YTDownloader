import flet as ft


class Theme:
    # Soulful Palette (Deep Indigo / Cyber-Violet / Neon Accents)

    # Primary: A vibrant, electric violet/indigo
    PRIMARY = "#6366F1"  # Indigo 500
    PRIMARY_DARK = "#4338CA"  # Indigo 700

    # Accent: A popping teal or pink for highlights
    ACCENT = "#EC4899"  # Pink 500
    ACCENT_SECONDARY = "#14B8A6"  # Teal 500

    # Backgrounds: Deep, rich darks (not just slate)
    BG_DARK = "#0B0F19"  # Very dark blue-grey/black
    BG_CARD = "#111827"  # Gray 900 (slightly lighter)
    BG_HOVER = "#1F2937"  # Gray 800

    # Glassmorphism hints
    BG_GLASS = ft.Colors.with_opacity(0.8, "#111827")

    # Text
    TEXT_PRIMARY = "#F3F4F6"  # Gray 100
    TEXT_SECONDARY = "#9CA3AF"  # Gray 400
    TEXT_MUTED = "#6B7280"  # Gray 500

    # Status Colors (Vibrant)
    SUCCESS = "#10B981"  # Emerald 500
    WARNING = "#F59E0B"  # Amber 500
    ERROR = "#EF4444"  # Red 500
    INFO = "#3B82F6"  # Blue 500

    # Borders
    BORDER = "#374151"  # Gray 700

    # Gradients
    GRADIENT_PRIMARY = ft.LinearGradient(
        begin=ft.alignment.top_left,
        end=ft.alignment.bottom_right,
        colors=[PRIMARY, ACCENT],
    )

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
                surface_tint=Theme.PRIMARY_DARK,  # Adds a slight tint to surface in M3
            ),
            visual_density=ft.VisualDensity.COMFORTABLE,
            page_transitions=ft.PageTransitionsTheme(
                android=ft.PageTransitionTheme.ZOOM,
                ios=ft.PageTransitionTheme.CUPERTINO,
                macos=ft.PageTransitionTheme.CUPERTINO,
                linux=ft.PageTransitionTheme.ZOOM,
                windows=ft.PageTransitionTheme.ZOOM,
            ),
            # Typography can be adjusted here if we imported a font
            # font_family="Roboto",
        )
