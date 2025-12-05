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
        return ft.Column(
            [
                ft.Text(
                    "Download Options",
                    weight=ft.FontWeight.BOLD,
                    color=Theme.Primary.MAIN,
                ),
                ft.Text("Standard download mode used.", color=Theme.Text.SECONDARY),
            ],
            spacing=10,
        )

    def get_options(self) -> Dict[str, Any]:
        return {
            "video_format": "best",
        }
