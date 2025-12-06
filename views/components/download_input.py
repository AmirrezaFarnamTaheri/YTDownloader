"""
Download Input Card Component.

This module defines the `DownloadInputCard` class, which is a UI component
for the download view containing URL input, fetch button, and various options.
"""

import flet as ft

from localization_manager import LocalizationManager as LM
from theme import Theme


class DownloadInputCard(ft.Container):
    """
    A card container for download inputs and options.

    Attributes:
        url_input (ft.TextField): Text field for URL input.
        fetch_btn (ft.IconButton): Button to trigger metadata fetching.
        video_format_dd (ft.Dropdown): Dropdown for video format selection.
        cookies_dd (ft.Dropdown): Dropdown for cookies selection.
        playlist_cb (ft.Checkbox): Checkbox for playlist downloading.
        sponsorblock_cb (ft.Checkbox): Checkbox for SponsorBlock.
        force_generic_cb (ft.Checkbox): Checkbox for forcing generic downloader.
        time_start (ft.TextField): Input for start time.
        time_end (ft.TextField): Input for end time.
    """

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments

    def __init__(
        self,
        url_input,
        fetch_btn,
        video_format_dd,
        cookies_dd,
        playlist_cb,
        sponsorblock_cb,
        force_generic_cb,
        time_start,
        time_end,
    ):
        super().__init__()
        self.url_input = url_input
        self.fetch_btn = fetch_btn
        self.video_format_dd = video_format_dd
        self.cookies_dd = cookies_dd
        self.playlist_cb = playlist_cb
        self.sponsorblock_cb = sponsorblock_cb
        self.force_generic_cb = force_generic_cb
        self.time_start = time_start
        self.time_end = time_end

        self.padding = 20
        self.bgcolor = Theme.BG_CARD
        self.border_radius = 16
        self.border = ft.border.all(1, Theme.BORDER)

        self.content = self._build_content()

    def _build_content(self):
        # Platform Icons - Wrap on small screens
        platform_icons = ft.Row(
            [
                ft.Icon(
                    ft.icons.ONDEMAND_VIDEO, color=ft.colors.RED_400, tooltip="YouTube"
                ),
                ft.Icon(
                    ft.icons.TELEGRAM, color=ft.colors.BLUE_400, tooltip="Telegram"
                ),
                ft.Icon(
                    ft.icons.ALTERNATE_EMAIL,
                    color=ft.colors.LIGHT_BLUE_400,
                    tooltip="Twitter/X",
                ),
                ft.Icon(
                    ft.icons.CAMERA_ALT, color=ft.colors.PINK_400, tooltip="Instagram"
                ),
                ft.Icon(ft.icons.LINK, color=Theme.TEXT_MUTED, tooltip="Generic Files"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            opacity=0.7,
            wrap=True,
        )

        # Options Row - Use wrap for responsiveness
        options_row = ft.Row(
            [
                self.video_format_dd,
                self.cookies_dd,
            ],
            wrap=True,
            spacing=10,
            run_spacing=10,
            alignment=ft.MainAxisAlignment.START,
        )

        checkboxes_row = ft.Row(
            [
                self.playlist_cb,
                self.sponsorblock_cb,
                self.force_generic_cb,
            ],
            alignment=ft.MainAxisAlignment.START,
            wrap=True,
            spacing=20,
            run_spacing=10,
        )

        time_row = ft.Row(
            [
                ft.Text(LM.get("time_range_label"), color=Theme.TEXT_MUTED),
                self.time_start,
                ft.Text("-"),
                self.time_end,
            ],
            alignment=ft.MainAxisAlignment.START,
            wrap=True,
            spacing=5,
            run_spacing=5,
        )

        # Main Input Row (URL + Button)
        input_row = ft.Row(
            [ft.Container(self.url_input, expand=True), self.fetch_btn],
            alignment=ft.MainAxisAlignment.CENTER,
            wrap=False,  # We want these side-by-side if possible, but URL expands
        )

        return ft.Column(
            [
                platform_icons,
                ft.Container(height=20),
                input_row,
                ft.Container(height=10),
                options_row,
                checkboxes_row,
                ft.Container(height=10),
                time_row,
            ]
        )
