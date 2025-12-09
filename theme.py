"""
Application theme definitions and constants.
"""

from typing import Any, Dict, Optional

import flet as ft


class Theme:
    """
    Main theme class containing color definitions and theme generation logic.
    Soulful Palette V3 (Refined, Higher Contrast, Modern).
    """

    # --- Colors ---
    # Primary: A vibrant, electric violet/indigo
    PRIMARY = "#818CF8"  # Indigo 400
    PRIMARY_DARK = "#4F46E5"  # Indigo 600

    # Accent: A popping pink for highlights
    ACCENT = "#F472B6"  # Pink 400
    ACCENT_SECONDARY = "#2DD4BF"  # Teal 400

    # Backgrounds: Deep, rich darks
    BG_DARK = "#0F172A"  # Slate 900
    BG_CARD = "#1E293B"  # Slate 800
    BG_HOVER = "#334155"  # Slate 700
    BG_INPUT = "#020617"  # Slate 950
    BG_SURFACE_VARIANT = "#1E293B"
    BG_LIGHT = "#1E293B"  # Light background used for sidebar in dark mode apps

    # Text
    TEXT_PRIMARY = "#F8FAFC"  # Slate 50
    TEXT_SECONDARY = "#94A3B8"  # Slate 400
    TEXT_MUTED = "#64748B"  # Slate 500

    # Status
    SUCCESS = "#34D399"  # Emerald 400
    WARNING = "#FBBF24"  # Amber 400
    ERROR = "#EF4444"  # Red 500
    INFO = "#60A5FA"  # Blue 400

    # Borders & Dividers
    BORDER = "#334155"  # Slate 700
    DIVIDER = "#334155"  # Alias for Divider color

    # --- Subclasses for Usage ---
    # NOTE: These reference the top-level color definitions above.
    # When updating colors, modify the top-level constants (BG_CARD, TEXT_PRIMARY, etc.)
    # pylint: disable=too-few-public-methods
    class Surface:
        """Surface color definitions."""

        # References: Theme.BG_CARD, Theme.BG_INPUT
        BG = "#1E293B"
        CARD = "#1E293B"
        INPUT = "#020617"

    # pylint: disable=too-few-public-methods
    class Primary:
        """Primary color definitions."""

        # References: Theme.PRIMARY
        MAIN = "#818CF8"

    class Text:
        """Text color definitions."""

        # References: Theme.TEXT_PRIMARY, Theme.TEXT_SECONDARY
        PRIMARY = "#F8FAFC"
        SECONDARY = "#94A3B8"

    class Divider:
        # pylint: disable=too-few-public-methods
        """Divider color definitions."""
        # References: Theme.DIVIDER
        COLOR = "#334155"

    class Status:
        """Status color definitions."""

        SUCCESS = "#34D399"
        ERROR = "#EF4444"

    @staticmethod
    def get_high_contrast_theme() -> ft.Theme:
        """Returns the High Contrast Theme object."""
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=ft.colors.YELLOW_400,
                secondary=ft.colors.CYAN_400,
                background=ft.colors.BLACK,
                surface=ft.colors.GREY_900,
                surface_variant=ft.colors.GREY_800,
                error=ft.colors.RED_500,
                on_primary=ft.colors.BLACK,
                on_secondary=ft.colors.BLACK,
                on_background=ft.colors.WHITE,
                on_surface=ft.colors.WHITE,
                surface_tint=ft.colors.TRANSPARENT,
                outline=ft.colors.WHITE,
                inverse_surface=ft.colors.WHITE,
                on_inverse_surface=ft.colors.BLACK,
            ),
            # pylint: disable=no-member
            visual_density=ft.VisualDensity.COMFORTABLE,
            page_transitions=ft.PageTransitionsTheme(
                android=ft.PageTransitionTheme.ZOOM,
                ios=ft.PageTransitionTheme.CUPERTINO,
                macos=ft.PageTransitionTheme.CUPERTINO,
                linux=ft.PageTransitionTheme.ZOOM,
                windows=ft.PageTransitionTheme.ZOOM,
            ),
            scrollbar_theme=ft.ScrollbarTheme(
                thumb_color=ft.colors.WHITE,
                radius=0,
                thickness=10,
                interactive=True,
            ),
        )

    @staticmethod
    def get_theme() -> ft.Theme:
        """Returns the Flet Theme object configured with application colors."""
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=Theme.PRIMARY,
                secondary=Theme.ACCENT,
                background=Theme.BG_DARK,
                surface=Theme.BG_CARD,
                surface_variant=Theme.BG_SURFACE_VARIANT,
                error=Theme.ERROR,
                on_primary=Theme.BG_DARK,
                on_secondary=Theme.BG_DARK,
                on_background=Theme.TEXT_PRIMARY,
                on_surface=Theme.TEXT_PRIMARY,
                surface_tint=ft.colors.TRANSPARENT,  # Removing tint for cleaner look
                outline=Theme.BORDER,
                inverse_surface=Theme.TEXT_PRIMARY,
                on_inverse_surface=Theme.BG_DARK,
                # pylint: disable=no-member
            ),
            # pylint: disable=no-member
            visual_density=ft.ThemeVisualDensity.COMFORTABLE,
            page_transitions=ft.PageTransitionsTheme(
                android=ft.PageTransitionTheme.ZOOM,
                ios=ft.PageTransitionTheme.CUPERTINO,
                macos=ft.PageTransitionTheme.CUPERTINO,
                linux=ft.PageTransitionTheme.ZOOM,
                windows=ft.PageTransitionTheme.ZOOM,
            ),
            # Scrollbar theme for better visibility
            scrollbar_theme=ft.ScrollbarTheme(
                thumb_color=Theme.BG_HOVER,
                radius=4,
                thickness=6,
                interactive=True,
            ),
        )

    @staticmethod
    def get_input_decoration(
        hint_text: str = "", prefix_icon: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Standardized Input Decoration properties.
        Returns a dictionary of properties to be unpacked into a TextField.
        """
        # Flet's TextField does not have an 'input_decoration' property.
        # It has direct properties for decoration.
        return {
            "filled": True,
            "bgcolor": Theme.BG_INPUT,
            "hint_text": hint_text,
            "hint_style": ft.TextStyle(color=Theme.TEXT_MUTED),
            "border": ft.InputBorder.OUTLINE,
            # pylint: disable=line-too-long
            "border_width": 0,  # Simulate 'no border' initially if desired, or use transparent color
            "border_color": ft.colors.TRANSPARENT,
            "focused_border_color": Theme.PRIMARY,
            "focused_border_width": 1,
            "content_padding": 15,
            "prefix_icon": prefix_icon,
            "dense": True,
            "border_radius": 8,
        }
