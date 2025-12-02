"""
Application theme definitions and constants.
"""

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

    # Text
    TEXT_PRIMARY = "#F8FAFC"  # Slate 50
    TEXT_SECONDARY = "#94A3B8"  # Slate 400
    TEXT_MUTED = "#64748B"  # Slate 500

    # Status
    SUCCESS = "#34D399"  # Emerald 400
    WARNING = "#FBBF24"  # Amber 400
    ERROR = "#EF4444"  # Red 500
    INFO = "#60A5FA"  # Blue 400

    # Borders
    BORDER = "#334155"  # Slate 700

    # --- Subclasses for Usage ---
    class Surface:
        BG = "#1E293B"
        CARD = "#1E293B"
        INPUT = "#020617"

    class Primary:
        MAIN = "#818CF8"

    class Text:
        PRIMARY = "#F8FAFC"
        SECONDARY = "#94A3B8"

    class Divider:
        COLOR = "#334155"

    class Status:
        SUCCESS = "#34D399"
        ERROR = "#EF4444"

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
                surface_tint=ft.Colors.TRANSPARENT,  # Removing tint for cleaner look
                outline=Theme.BORDER,
                inverse_surface=Theme.TEXT_PRIMARY,
                on_inverse_surface=Theme.BG_DARK,
            ),
            visual_density=ft.VisualDensity.COMFORTABLE,
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
            # Standardize font (optional, if custom fonts were included)
            # font_family="Roboto",
        )

    @staticmethod
    def get_input_decoration(hint_text: str = "", prefix_icon: str = None):
        """
        Standardized Input Decoration.
        Note: Removed explicit return type hint to avoid AttributeError in some envs where flet.InputDecoration is not exposed.
        """
        return ft.InputDecoration(
            filled=True,
            fill_color=Theme.BG_INPUT,
            hint_text=hint_text,
            hint_style=ft.TextStyle(color=Theme.TEXT_MUTED),
            border=ft.OutlineInputBorder(
                border_side=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                border_radius=8,
            ),
            focused_border=ft.OutlineInputBorder(
                border_side=ft.BorderSide(1, Theme.PRIMARY),
                border_radius=8,
            ),
            content_padding=15,
            prefix_icon=prefix_icon,
            is_dense=True,  # Improved density
        )
