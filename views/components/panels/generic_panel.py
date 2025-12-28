"""
Generic download panel.
"""

from collections.abc import Callable
from typing import Any

import flet as ft

from theme import Theme
from views.components.panels.base_panel import BasePanel


class GenericPanel(BasePanel):
    """
    Panel for generic downloads.
    """

    def __init__(self, info: dict[str, Any], on_option_change: Callable):
        super().__init__(info, on_option_change)
        self.content = self.build()

    def build(self):
        # pylint: disable=import-outside-toplevel
        from localization_manager import LocalizationManager as LM

        self.format_dd = ft.Dropdown(
            label=LM.get("video_format", "Format"),
            options=[
                ft.dropdown.Option("best", LM.get("best_quality")),
                ft.dropdown.Option("audio", LM.get("audio_only")),
            ],
            value="best",
            on_change=lambda e: self.on_option_change(),
            **Theme.get_input_decoration(prefix_icon=ft.icons.SETTINGS_ETHERNET),
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        LM.get("download_options"),
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=Theme.Primary.MAIN,
                    ),
                    ft.Text(
                        LM.get("generic_download_mode"), color=Theme.Text.SECONDARY
                    ),
                    self.format_dd,
                ],
                spacing=15,
            ),
            **Theme.get_card_decoration(),
        )

    def get_options(self) -> dict[str, Any]:
        return {
            "video_format": self.format_dd.value,
        }
