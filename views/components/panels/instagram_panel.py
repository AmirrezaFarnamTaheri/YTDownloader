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

        self.warning_text = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.WARNING_AMBER, color=Theme.Status.WARNING),
                    ft.Text(
                        LM.get("instagram_story_requires_cookies"),
                        color=Theme.Status.WARNING,
                        size=12,
                        expand=True,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            visible=False,
            padding=10,
            bgcolor=ft.colors.with_opacity(0.1, Theme.Status.WARNING),
            border_radius=8,
        )

        self.download_type = ft.RadioGroup(
            content=ft.Row(
                [
                    ft.Radio(
                        value="post",
                        label=LM.get("instagram_post_reel"),
                        active_color=Theme.Primary.MAIN,
                    ),
                    ft.Radio(
                        value="story",
                        label=LM.get("instagram_story"),
                        active_color=Theme.Primary.MAIN,
                    ),
                ],
                spacing=20,
            ),
            value="post",
            on_change=self._on_type_change,
        )

        self.content = self.build()

    def _on_type_change(self, e):
        # pylint: disable=unused-argument
        self.warning_text.visible = self.download_type.value == "story"
        self.warning_text.update()
        self.on_option_change()

    def build(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        LM.get("instagram_options"),
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=Theme.Primary.MAIN,
                    ),
                    self.download_type,
                    self.warning_text,
                ],
                spacing=15,
            ),
            **Theme.get_card_decoration()
        )

    def get_options(self) -> Dict[str, Any]:
        return {
            "insta_type": self.download_type.value,
            # Instagram usually implies best quality available
            "video_format": "best",
        }
