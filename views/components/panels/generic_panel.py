"""
Generic download panel.
"""

from typing import Any, Callable, Dict

import flet as ft

from theme import Theme
from views.components.panels.base_panel import BasePanel


class GenericPanel(BasePanel):
    """
    Panel for generic downloads.
    """

    def __init__(self, info: Dict[str, Any], on_option_change: Callable):
        super().__init__(info, on_option_change)
        self.content = self.build()

    def build(self):
        # pylint: disable=import-outside-toplevel
        from localization_manager import LocalizationManager as LM

        self.format_dd = ft.Dropdown(
            label=LM.get("video_format", "Format"),
            options=[
                ft.dropdown.Option("best", "Best Quality"),
                ft.dropdown.Option("audio", "Audio Only"),
            ],
            value="best",
            on_change=lambda e: self.on_option_change(),
            border_color=Theme.BORDER,
            border_radius=8,
        )

        return ft.Column(
            [
                ft.Text(
                    LM.get("download_options"),
                    weight=ft.FontWeight.BOLD,
                    color=Theme.Primary.MAIN,
                ),
                ft.Text(LM.get("generic_download_mode"), color=Theme.Text.SECONDARY),
                self.format_dd,
            ],
            spacing=10,
        )

    def get_options(self) -> Dict[str, Any]:
        return {
            "video_format": self.format_dd.value,
        }
