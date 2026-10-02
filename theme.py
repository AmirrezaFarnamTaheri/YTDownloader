"""
Application theme definitions and constants.

Provides a dual (dark / light) palette and a small runtime helper so the UI
can respect the user's theme-mode selection without sprinkling conditional
branches throughout the codebase.
"""

from typing import Any

import flet as ft


class _DarkPalette:
    """Dark-mode palette."""

    PRIMARY = "#14B8A6"
    PRIMARY_DARK = "#0F766E"
    ACCENT = "#F97316"
    ACCENT_SECONDARY = "#84CC16"

    BG = "#0B1220"
    BG_CARD = "#111C2E"
    BG_HOVER = "#1E2A40"
    BG_INPUT = "#08101D"
    BG_SURFACE_VARIANT = "#152238"
    BG_NAV = "#0E172A"

    TEXT_PRIMARY = "#F1F5F9"
    TEXT_SECONDARY = "#CBD5E1"
    TEXT_MUTED = "#94A3B8"

    SUCCESS = "#22C55E"
    WARNING = "#F59E0B"
    ERROR = "#EF4444"
    INFO = "#38BDF8"

    BORDER = "#334155"
    DIVIDER = "#334155"
    SHADOW = ft.colors.with_opacity(0.25, ft.colors.BLACK)


class _LightPalette:
    """Light-mode palette."""

    PRIMARY = "#0D9488"
    PRIMARY_DARK = "#0F766E"
    ACCENT = "#EA580C"
    ACCENT_SECONDARY = "#65A30D"

    BG = "#F8FAFC"
    BG_CARD = "#FFFFFF"
    BG_HOVER = "#F1F5F9"
    BG_INPUT = "#F1F5F9"
    BG_SURFACE_VARIANT = "#E2E8F0"
    BG_NAV = "#FFFFFF"

    TEXT_PRIMARY = "#0F172A"
    TEXT_SECONDARY = "#334155"
    TEXT_MUTED = "#64748B"

    SUCCESS = "#16A34A"
    WARNING = "#D97706"
    ERROR = "#DC2626"
    INFO = "#0284C7"

    BORDER = "#CBD5E1"
    DIVIDER = "#E2E8F0"
    SHADOW = ft.colors.with_opacity(0.08, ft.colors.BLACK)


class Theme:
    """
    Main theme class with dynamic dark/light resolution.

    Access active colors through ``Theme.<name>`` class attributes — they are
    swapped at runtime by :func:`apply_theme_mode` when the user changes the
    theme setting.  Import sites that were written against the old dark-only
    constants continue to work unchanged.
    """

    # --- Active palette (defaults to dark; updated via apply_theme_mode) ---
    PRIMARY: str = _DarkPalette.PRIMARY
    PRIMARY_DARK: str = _DarkPalette.PRIMARY_DARK
    ACCENT: str = _DarkPalette.ACCENT
    ACCENT_SECONDARY: str = _DarkPalette.ACCENT_SECONDARY

    BG_DARK: str = _DarkPalette.BG
    BG_CARD: str = _DarkPalette.BG_CARD
    BG_HOVER: str = _DarkPalette.BG_HOVER
    BG_INPUT: str = _DarkPalette.BG_INPUT
    BG_SURFACE_VARIANT: str = _DarkPalette.BG_SURFACE_VARIANT
    BG_LIGHT: str = _DarkPalette.BG_NAV

    TEXT_PRIMARY: str = _DarkPalette.TEXT_PRIMARY
    TEXT_SECONDARY: str = _DarkPalette.TEXT_SECONDARY
    TEXT_MUTED: str = _DarkPalette.TEXT_MUTED

    SUCCESS: str = _DarkPalette.SUCCESS
    WARNING: str = _DarkPalette.WARNING
    ERROR: str = _DarkPalette.ERROR
    INFO: str = _DarkPalette.INFO

    BORDER: str = _DarkPalette.BORDER
    DIVIDER: str = _DarkPalette.DIVIDER

    is_dark: bool = True

    # --- Typography ---
    FONT_FAMILY = "Poppins, Nunito Sans, Segoe UI, sans-serif"
    FONT_SIZE_BODY = 14
    FONT_SIZE_TITLE = 20
    FONT_SIZE_HEADER = 24
    FONT_SIZE_SMALL = 12

    # --- Spacing ---
    PADDING_SMALL = 10
    PADDING_MEDIUM = 20
    PADDING_LARGE = 30
    BORDER_RADIUS = 12

    # --- Nested class proxies (kept for backward compatibility) ---
    # These are re-bound in apply_theme_mode.
    class Surface:  # type: ignore[no-redef]
        """Surface color definitions (re-bound by apply_theme_mode)."""

        BG: str = _DarkPalette.BG_CARD
        CARD: str = _DarkPalette.BG_CARD
        INPUT: str = _DarkPalette.BG_INPUT

    class Primary:  # type: ignore[no-redef]
        """Primary color definitions (re-bound by apply_theme_mode)."""

        MAIN: str = _DarkPalette.PRIMARY

    class Text:  # type: ignore[no-redef]
        """Text color definitions (re-bound by apply_theme_mode)."""

        PRIMARY: str = _DarkPalette.TEXT_PRIMARY
        SECONDARY: str = _DarkPalette.TEXT_SECONDARY

    class Divider:  # type: ignore[no-redef]
        """Divider color definitions (re-bound by apply_theme_mode)."""

        COLOR: str = _DarkPalette.DIVIDER

    class Status:  # type: ignore[no-redef]
        """Status color definitions (re-bound by apply_theme_mode)."""

        SUCCESS: str = _DarkPalette.SUCCESS
        ERROR: str = _DarkPalette.ERROR
        WARNING: str = _DarkPalette.WARNING
        INFO: str = _DarkPalette.INFO

    @classmethod
    def apply_theme_mode(cls, mode: str = "dark") -> None:
        """Swap active palette to dark, light, or high-contrast."""
        mode = (mode or "dark").strip().lower()
        if mode in {"high contrast", "high_contrast", "high-contrast"}:
            # High contrast is a special Flet theme; keep dark defaults here.
            palette: Any = _DarkPalette
            cls.is_dark = True
        elif mode == "light":
            palette = _LightPalette
            cls.is_dark = False
        else:
            palette = _DarkPalette
            cls.is_dark = True

        cls.PRIMARY = palette.PRIMARY
        cls.PRIMARY_DARK = palette.PRIMARY_DARK
        cls.ACCENT = palette.ACCENT
        cls.ACCENT_SECONDARY = palette.ACCENT_SECONDARY
        cls.BG_DARK = palette.BG
        cls.BG_CARD = palette.BG_CARD
        cls.BG_HOVER = palette.BG_HOVER
        cls.BG_INPUT = palette.BG_INPUT
        cls.BG_SURFACE_VARIANT = palette.BG_SURFACE_VARIANT
        cls.BG_LIGHT = palette.BG_NAV
        cls.TEXT_PRIMARY = palette.TEXT_PRIMARY
        cls.TEXT_SECONDARY = palette.TEXT_SECONDARY
        cls.TEXT_MUTED = palette.TEXT_MUTED
        cls.SUCCESS = palette.SUCCESS
        cls.WARNING = palette.WARNING
        cls.ERROR = palette.ERROR
        cls.INFO = palette.INFO
        cls.BORDER = palette.BORDER
        cls.DIVIDER = palette.DIVIDER

        cls.Surface.BG = palette.BG_CARD
        cls.Surface.CARD = palette.BG_CARD
        cls.Surface.INPUT = palette.BG_INPUT
        cls.Primary.MAIN = palette.PRIMARY
        cls.Text.PRIMARY = palette.TEXT_PRIMARY
        cls.Text.SECONDARY = palette.TEXT_SECONDARY
        cls.Divider.COLOR = palette.DIVIDER
        cls.Status.SUCCESS = palette.SUCCESS
        cls.Status.ERROR = palette.ERROR
        cls.Status.WARNING = palette.WARNING
        cls.Status.INFO = palette.INFO

    @classmethod
    def get_surface_gradient(cls) -> ft.LinearGradient:
        """Background gradient for primary content surfaces."""
        if cls.is_dark:
            return ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[cls.BG_DARK, cls.BG_CARD],
            )
        # Flat light surface feels cleaner than a gradient
        return ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[cls.BG_DARK, cls.BG_DARK],
        )

    @classmethod
    def get_sidebar_gradient(cls) -> ft.LinearGradient:
        """Background gradient for navigation surfaces."""
        if cls.is_dark:
            return ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=[cls.BG_LIGHT, cls.BG_CARD],
            )
        return ft.LinearGradient(
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
            colors=[cls.BG_LIGHT, cls.BG_LIGHT],
        )

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
            "hint_style": ft.TextStyle(
                color=Theme.TEXT_MUTED, size=Theme.FONT_SIZE_BODY
            ),
            "label_style": ft.TextStyle(
                color=Theme.TEXT_SECONDARY, size=Theme.FONT_SIZE_BODY
            ),
            "text_style": ft.TextStyle(
                color=Theme.TEXT_PRIMARY, size=Theme.FONT_SIZE_BODY
            ),
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

    @classmethod
    def get_card_decoration(cls) -> dict[str, Any]:
        """Standardized card decoration that adapts to the active palette."""
        shadow_opacity = 0.18 if cls.is_dark else 0.06
        return {
            "bgcolor": cls.BG_CARD,
            "border_radius": cls.BORDER_RADIUS,
            "padding": cls.PADDING_MEDIUM,
            "shadow": ft.BoxShadow(
                blur_radius=14,
                spread_radius=0,
                color=ft.colors.with_opacity(shadow_opacity, ft.colors.BLACK),
                offset=ft.Offset(0, 4),
            ),
            "border": ft.border.all(1, cls.BORDER),
        }
