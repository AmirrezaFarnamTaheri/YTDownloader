"""
Download Preview Card Component.

Displays a preview of the video/content to be downloaded, including thumbnail,
title, author, and duration.
Refactored for high-impact visual appeal.
"""

import flet as ft

from localization_manager import LocalizationManager as LM
from theme import Theme


class DownloadPreviewCard(ft.Container):
    """
    A card container for displaying video preview information.

    Attributes:
        thumbnail (ft.Image): The thumbnail image.
        title_text (ft.Text): The video title text.
        duration_text (ft.Text): The video duration text.
        author_text (ft.Text): The video uploader/author text.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self):
        super().__init__()
        self.visible = False

        # Apply theme decoration
        style = Theme.get_card_decoration()
        for k, v in style.items():
            setattr(self, k, v)

        self.padding = 0  # Custom padding for this card layout
        self.clip_behavior = ft.ClipBehavior.HARD_EDGE  # Clip thumbnail rounded corners

        self.thumbnail = ft.Image(
            src="",
            width=320,
            height=180,
            fit=ft.ImageFit.COVER,
            border_radius=ft.border_radius.only(top_left=12, bottom_left=12),
        )

        # Responsive thumbnail logic (on mobile it might need to be top)
        # For now, keeping side-by-side for desktop-first feel

        self.title_text = ft.Text(
            LM.get("video_title_placeholder"),
            size=18,
            weight=ft.FontWeight.BOLD,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=Theme.Text.PRIMARY,
        )

        self.duration_text = ft.Text(
            "00:00", size=13, color=Theme.TEXT_MUTED, weight=ft.FontWeight.W_500
        )

        self.author_text = ft.Text(
            LM.get("channel_placeholder"),
            size=14,
            color=Theme.Primary.MAIN,
            weight=ft.FontWeight.BOLD,
        )

        # Meta tags container (e.g. Duration, Quality hint)
        self.meta_row = ft.Row(
            [
                ft.Icon(ft.icons.TIMER, size=16, color=Theme.TEXT_MUTED),
                self.duration_text,
            ],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.content = ft.Row(
            [
                self.thumbnail,
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Container(height=5),  # Spacer
                            self.title_text,
                            ft.Container(height=5),
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.icons.PERSON,
                                        size=16,
                                        color=Theme.Primary.MAIN,
                                    ),
                                    self.author_text,
                                ],
                                spacing=5,
                            ),
                            ft.Container(height=10),
                            self.meta_row,
                            # We could add a "Ready to Download" badge here
                        ],
                        expand=True,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    padding=20,
                    expand=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=0,
        )

    def update_info(self, info: dict):
        """
        Updates the preview card with video information.

        Args:
            info (dict): A dictionary containing video metadata (title, thumbnail, etc.).
        """
        if not info:
            self.visible = False
            self.update()
            return

        self.title_text.value = info.get("title", LM.get("unknown_title"))
        self.thumbnail.src = info.get("thumbnail", "")
        duration = info.get("duration_string") or info.get("duration")
        self.duration_text.value = str(duration) if duration else "N/A"
        self.author_text.value = info.get("uploader", LM.get("unknown_channel"))

        self.visible = True
        self.update()
