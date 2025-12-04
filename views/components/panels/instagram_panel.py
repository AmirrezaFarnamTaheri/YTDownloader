"""
Instagram specific download panel.
"""

from typing import Any, Callable, Dict

import flet as ft

from localization_manager import LocalizationManager as LM
from theme import Theme
from views.components.panels.base_panel import BasePanel


class InstagramPanel(BasePanel):
    """
    Panel for Instagram downloads.
    """

    def __init__(self, info: Dict[str, Any], on_option_change: Callable):
        super().__init__(info, on_option_change)

        self.download_type = ft.RadioGroup(
            content=ft.Row(
                [
                    ft.Radio(value="post", label="Post/Reel"),
                    ft.Radio(value="story", label="Story"),
                ]
            ),
            value="post",
        )

        self.content = self.build()

    def build(self):
        return ft.Column(
            [
                ft.Text(
                    "Instagram Options",
                    weight=ft.FontWeight.BOLD,
                    color=Theme.Primary.MAIN,
                ),
                self.download_type,
            ],
            spacing=10,
        )

    def get_options(self) -> Dict[str, Any]:
        return {
            "insta_type": self.download_type.value,
            # Instagram usually implies best quality available
            "video_format": "best",
        }
