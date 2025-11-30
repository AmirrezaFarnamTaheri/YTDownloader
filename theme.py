"""
Application theme definitions and constants.
"""

import flet as ft


class Theme:
    """
    Main theme class containing color definitions and theme generation logic.
    Soulful Palette V2 (Refined, Higher Contrast, Modern).
    """

    # Primary: A vibrant, electric violet/indigo
    PRIMARY = "#818CF8"  # Indigo 400 - lighter for better contrast on dark
    PRIMARY_DARK = "#4F46E5"  # Indigo 600

    # Accent: A popping teal or pink for highlights
    ACCENT = "#F472B6"  # Pink 400
    ACCENT_SECONDARY = "#2DD4BF"  # Teal 400

    # Backgrounds: Deep, rich darks (not just slate)
    BG_DARK = "#0F172A"  # Slate 900
    BG_CARD = "#1E293B"  # Slate 800
    BG_HOVER = "#334155"  # Slate 700

    # Inputs
    BG_INPUT = "#0F172A"  # Darker than card for depth

    # Glassmorphism hints
    BG_GLASS = ft.Colors.with_opacity(0.9, "#1E293B")

    # Text
    TEXT_PRIMARY = "#F8FAFC"  # Slate 50
    TEXT_SECONDARY = "#94A3B8"  # Slate 400
    TEXT_MUTED = "#64748B"  # Slate 500

    # Status Colors (Vibrant)
    SUCCESS = "#34D399"  # Emerald 400
    WARNING = "#FBBF24"  # Amber 400
    ERROR = "#F87171"  # Red 400
    INFO = "#60A5FA"  # Blue 400

    # Borders
    BORDER = "#334155"  # Slate 700

    # Gradients
    GRADIENT_PRIMARY = ft.LinearGradient(
        begin=ft.alignment.top_left,
        end=ft.alignment.bottom_right,
        colors=[PRIMARY, ACCENT],
    )

    # Sub-classes for better organization (and to fix test attribute errors)
    class Surface:
        """Surface colors."""

        BG = "#1E293B"  # Same as BG_CARD

    class Primary:
        """Primary colors."""

        MAIN = "#818CF8"  # Same as PRIMARY

    class Text:
        """Text colors."""

        PRIMARY = "#F8FAFC"

    class Divider:
        """Divider colors."""

        COLOR = "#334155"  # Same as BORDER

    @staticmethod
    def get_theme():
        """Returns the Flet Theme object configured with application colors."""
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=Theme.PRIMARY,
                secondary=Theme.ACCENT,
                background=Theme.BG_DARK,
                surface=Theme.BG_CARD,
                error=Theme.ERROR,
                on_primary=Theme.BG_DARK,  # Dark text on light primary
                on_secondary=Theme.BG_DARK,
                on_background=Theme.TEXT_PRIMARY,
                on_surface=Theme.TEXT_PRIMARY,
                surface_tint=Theme.PRIMARY,
                outline=Theme.BORDER,
            ),
            visual_density=ft.VisualDensity.COMFORTABLE,
            page_transitions=ft.PageTransitionsTheme(
                android=ft.PageTransitionTheme.ZOOM,
                ios=ft.PageTransitionTheme.CUPERTINO,
                macos=ft.PageTransitionTheme.CUPERTINO,
                linux=ft.PageTransitionTheme.ZOOM,
                windows=ft.PageTransitionTheme.ZOOM,
            ),
            # Use platform default font or Roboto if available
        )
