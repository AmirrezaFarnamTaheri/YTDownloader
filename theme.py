"""
Application theme definitions and constants.
Refined Soulful Palette V4 (Polished Typography & Spacing).
"""

from typing import Any

import flet as ft


class Theme:
    """
    Main theme class containing color definitions, typography, and theme generation logic.
    Soulful Palette V4 (Refined, Higher Contrast, Modern).
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

    # --- Typography Constants ---
    FONT_FAMILY = "Roboto, Segoe UI, sans-serif"
    FONT_SIZE_BODY = 14
    FONT_SIZE_TITLE = 20
    FONT_SIZE_HEADER = 24
    FONT_SIZE_SMALL = 12

    # --- Spacing Constants ---
    PADDING_SMALL = 10
    PADDING_MEDIUM = 20
    PADDING_LARGE = 30
    BORDER_RADIUS = 12

    # --- Subclasses for Usage ---
    # pylint: disable=too-few-public-methods
    class Surface:
        """Surface color definitions."""

        BG = "#1E293B"
        CARD = "#1E293B"
        INPUT = "#020617"

    class Primary:
        """Primary color definitions."""

        MAIN = "#818CF8"

    class Text:
        """Text color definitions."""

        PRIMARY = "#F8FAFC"
        SECONDARY = "#94A3B8"

    class Divider:
        """Divider color definitions."""

        COLOR = "#334155"

    class Status:
        """Status color definitions."""

        SUCCESS = "#34D399"
        ERROR = "#EF4444"
        WARNING = "#FBBF24"
        INFO = "#60A5FA"

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
            visual_density=ft.ThemeVisualDensity.COMFORTABLE,
            font_family=Theme.FONT_FAMILY,
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
                thickness=12,
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
                surface_tint=ft.colors.TRANSPARENT,
                outline=Theme.BORDER,
                inverse_surface=Theme.TEXT_PRIMARY,
                on_inverse_surface=Theme.BG_DARK,
                # pylint: disable=no-member
            ),
            # pylint: disable=no-member
            visual_density=ft.ThemeVisualDensity.COMFORTABLE,
            font_family=Theme.FONT_FAMILY,
            page_transitions=ft.PageTransitionsTheme(
                android=ft.PageTransitionTheme.ZOOM,
                ios=ft.PageTransitionTheme.CUPERTINO,
                macos=ft.PageTransitionTheme.CUPERTINO,
                linux=ft.PageTransitionTheme.ZOOM,
                windows=ft.PageTransitionTheme.ZOOM,
            ),
            scrollbar_theme=ft.ScrollbarTheme(
                thumb_color=Theme.BG_HOVER,
                radius=6,
                thickness=8,
                interactive=True,
            ),
        )

    @staticmethod
    def get_input_decoration(
        hint_text: str = "",
        prefix_icon: str | None = None,
        suffix_icon: str | None = None,
    ) -> dict[str, Any]:
        """
        Standardized Input Decoration properties.
        """
        data = {
            "filled": True,
            "bgcolor": Theme.BG_INPUT,
            "hint_text": hint_text,
            "hint_style": ft.TextStyle(color=Theme.TEXT_MUTED, size=Theme.FONT_SIZE_BODY),
            "label_style": ft.TextStyle(color=Theme.TEXT_SECONDARY, size=Theme.FONT_SIZE_BODY),
            "text_style": ft.TextStyle(color=Theme.TEXT_PRIMARY, size=Theme.FONT_SIZE_BODY),
            "border": ft.InputBorder.OUTLINE,
            "border_width": 1,
            "border_color": Theme.BORDER,
            "focused_border_color": Theme.PRIMARY,
            "focused_border_width": 2,
            "content_padding": 18,
            "dense": True,
            "border_radius": 8,
        }
        if prefix_icon:
            data["prefix_icon"] = prefix_icon
        if suffix_icon:
            data["suffix_icon"] = suffix_icon
        return data

    @staticmethod
    def get_card_decoration() -> dict[str, Any]:
        """
        Standardized Card Decoration.
        """
        return {
            "bgcolor": Theme.BG_CARD,
            "border_radius": Theme.BORDER_RADIUS,
            "padding": Theme.PADDING_MEDIUM,
            "shadow": ft.BoxShadow(
                blur_radius=12,
                spread_radius=1,
                color=ft.colors.with_opacity(0.15, ft.colors.BLACK),
                offset=ft.Offset(0, 4),
            ),
            "border": ft.border.all(1, Theme.BORDER),
        }
