"""
Dashboard View Module.

Features a modern dashboard with system status, quick actions,
active download summaries, and recent history.
Refactored to use Charts for better visualization.
"""

import logging
import shutil
from collections.abc import Callable

import flet as ft

from history_manager import HistoryManager
from localization_manager import LocalizationManager as LM
from theme import Theme
from ui_utils import open_folder
from views.base_view import BaseView
from views.components.history_item import HistoryItemControl

logger = logging.getLogger(__name__)


class DashboardView(BaseView):
    """
    Dashboard view serving as the home screen.

    Features:
    - System storage status (PieChart)
    - Active downloads counter and statistics (Cards)
    - Activity history (BarChart - Placeholder for now)
    - Recent download history
    """

    def __init__(
        self,
        on_navigate: Callable[[int], None],
        on_paste_url: Callable[[], None],
        on_batch_import: Callable[[], None],
        queue_manager,
    ):
        super().__init__(LM.get("dashboard"), ft.icons.DASHBOARD)
        self.on_navigate = on_navigate
        self.on_paste_url = on_paste_url
        self.on_batch_import = on_batch_import
        self.queue_manager = queue_manager

        # Widgets
        self.status_cards_row = ft.Row(spacing=20, wrap=True)

        # Storage Pie Chart
        self.storage_chart = ft.PieChart(
            sections=[],
            sections_space=0,
            center_space_radius=40,
            height=150,
        )
        self.storage_text = ft.Text(
            LM.get("storage_calculating"), size=12, color=Theme.TEXT_MUTED
        )

        # Activity Bar Chart (Placeholder for Phase 3 req)
        # Assuming simple activity stats for now
        self.activity_chart = ft.BarChart(
            bar_groups=[],
            border=ft.border.all(1, Theme.BORDER),
            left_axis=ft.ChartAxis(
                labels_size=40, title=ft.Text("Downloads", size=10)
            ),
            bottom_axis=ft.ChartAxis(
                labels_size=40, title=ft.Text("Day", size=10)
            ),
            horizontal_grid_lines=ft.ChartGridLines(
                color=Theme.BORDER, width=1, dash_pattern=[3, 3]
            ),
            tooltip_bgcolor=Theme.BG_CARD,
            max_y=10, # Dynamic
            interactive=True,
            height=150,
        )

        # Active downloads stats widgets
        self.active_downloads_text = ft.Text(
            "0", size=32, weight=ft.FontWeight.BOLD, color=Theme.Primary.MAIN
        )
        self.queued_downloads_text = ft.Text(
            "0", size=32, weight=ft.FontWeight.BOLD, color=Theme.ACCENT
        )
        self.completed_downloads_text = ft.Text(
            "0", size=32, weight=ft.FontWeight.BOLD, color=Theme.Status.SUCCESS
        )

        self.recent_history_list = ft.Column(spacing=10)

        self.content_area = ft.Container(
            content=ft.Column(
                [
                    # Welcome & Quick Actions
                    self._build_header_section(),
                    ft.Container(height=20),
                    # Download Statistics
                    self._build_stats_section(),
                    ft.Container(height=20),
                    # Charts Row
                    ft.Row([
                        ft.Column([
                            ft.Text(LM.get("system_status"), weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Column([self.storage_chart, self.storage_text], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                **Theme.get_card_decoration(),
                                width=300,
                                # Removed explicit padding=20 here to avoid collision with get_card_decoration
                            )
                        ]),
                         ft.Column([
                            ft.Text("Activity (Last 7 Days)", weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=self.activity_chart,
                                **Theme.get_card_decoration(),
                                width=400,
                                height=230
                                # Removed explicit padding=20 here too
                            )
                        ], expand=True),
                    ], wrap=True, alignment=ft.MainAxisAlignment.START, spacing=20),

                    ft.Container(height=20),
                    # Recent History
                    ft.Text(
                        LM.get("recent_history", "Recent History"),
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=Theme.Text.PRIMARY,
                    ),
                    ft.Container(
                        content=self.recent_history_list, **Theme.get_card_decoration()
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=10,
        )

        self.controls = [self.content_area]

    def _build_header_section(self):
        """Builds the top section with Greeting and Quick Actions."""

        # Quick Action Button Helper
        def quick_btn(icon, text, on_click, color):
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(icon, size=32, color=color),
                        ft.Text(
                            text, weight=ft.FontWeight.BOLD, color=Theme.Text.PRIMARY
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                width=160,
                height=100,
                **Theme.get_card_decoration(),
                on_click=on_click,
                ink=True,
            )

        return ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            LM.get("dashboard_welcome", "Welcome back!"),
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=Theme.Text.PRIMARY,
                        ),
                        ft.Text(
                            LM.get(
                                "dashboard_subtitle", "Ready to download something new?"
                            ),
                            size=16,
                            color=Theme.TEXT_SECONDARY,
                        ),
                    ],
                    expand=True,
                ),
                # Index 1 is Download View
                quick_btn(
                    ft.icons.ADD_LINK,
                    LM.get("quick_download", "New Download"),
                    lambda _: self.on_navigate(1),
                    Theme.ACCENT,
                ),
                quick_btn(
                    ft.icons.FILE_UPLOAD,
                    LM.get("batch_import"),
                    lambda _: self.on_batch_import(),
                    Theme.ACCENT_SECONDARY,
                ),
            ],
            wrap=True,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_stats_section(self):
        """Builds the download statistics section with cards."""

        def stat_card(title: str, value_widget: ft.Text, icon: str, color: str):
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon, size=40, color=color),
                        ft.Column(
                            [
                                value_widget,
                                ft.Text(title, size=12, color=Theme.Text.SECONDARY),
                            ],
                            spacing=2,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=15,
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                **Theme.get_card_decoration(),
                width=200,
                on_click=lambda _: self.on_navigate(2),  # Navigate to queue
                ink=True,
            )

        return ft.Column(
            [
                ft.Text(
                    LM.get("download_stats", "Download Statistics"),
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=Theme.Text.PRIMARY,
                ),
                ft.Row(
                    [
                        stat_card(
                            LM.get("active", "Active"),
                            self.active_downloads_text,
                            ft.icons.DOWNLOADING,
                            Theme.Primary.MAIN,
                        ),
                        stat_card(
                            LM.get("queued", "Queued"),
                            self.queued_downloads_text,
                            ft.icons.QUEUE,
                            Theme.ACCENT,
                        ),
                        stat_card(
                            LM.get("completed", "Completed"),
                            self.completed_downloads_text,
                            ft.icons.CHECK_CIRCLE,
                            Theme.Status.SUCCESS,
                        ),
                    ],
                    spacing=15,
                    wrap=True,
                ),
            ],
            spacing=10,
        )

    def load(self):
        """Refreshes the dashboard data."""
        self._refresh_storage()
        self._refresh_stats()
        self._refresh_history()
        self._refresh_activity() # New
        if self.page:
            self.update()

    def _refresh_activity(self):
        """
        Refresh activity chart.
        Mock implementation for now as HistoryManager aggregation isn't available.
        """
        # In a real impl, we'd query HistoryManager.get_stats_by_day()
        # For now, show dummy data to demonstrate UI component
        self.activity_chart.bar_groups = [
            ft.BarChartGroup(x=0, bar_rods=[ft.BarChartRod(from_y=0, to_y=5, color=Theme.Primary.MAIN, width=15, border_radius=4)]),
            ft.BarChartGroup(x=1, bar_rods=[ft.BarChartRod(from_y=0, to_y=8, color=Theme.Primary.MAIN, width=15, border_radius=4)]),
            ft.BarChartGroup(x=2, bar_rods=[ft.BarChartRod(from_y=0, to_y=3, color=Theme.Primary.MAIN, width=15, border_radius=4)]),
            ft.BarChartGroup(x=3, bar_rods=[ft.BarChartRod(from_y=0, to_y=6, color=Theme.Primary.MAIN, width=15, border_radius=4)]),
            ft.BarChartGroup(x=4, bar_rods=[ft.BarChartRod(from_y=0, to_y=1, color=Theme.Primary.MAIN, width=15, border_radius=4)]),
        ]
        self.activity_chart.bottom_axis.labels = [
             ft.ChartAxisLabel(value=0, label=ft.Text("M", size=10)),
             ft.ChartAxisLabel(value=1, label=ft.Text("T", size=10)),
             ft.ChartAxisLabel(value=2, label=ft.Text("W", size=10)),
             ft.ChartAxisLabel(value=3, label=ft.Text("T", size=10)),
             ft.ChartAxisLabel(value=4, label=ft.Text("F", size=10)),
        ]
        self.activity_chart.update()

    def _refresh_stats(self):
        """Updates download statistics from queue manager."""
        try:
            if hasattr(self.queue_manager, "get_statistics"):
                stats = self.queue_manager.get_statistics()
            else:
                # Fallback for older queue manager
                items = self.queue_manager.get_all()
                stats = {
                    "downloading": sum(
                        1 for i in items if i.get("status") == "Downloading"
                    ),
                    "queued": sum(1 for i in items if i.get("status") == "Queued" or i.get("status") == "Allocating"),
                    "completed": sum(
                        1 for i in items if i.get("status") == "Completed"
                    ),
                }

            self.active_downloads_text.value = str(stats.get("downloading", 0))
            self.queued_downloads_text.value = str(stats.get("queued", 0))
            self.completed_downloads_text.value = str(stats.get("completed", 0))

        except Exception as e:
            logger.debug("Error refreshing stats: %s", e)
            self.active_downloads_text.value = "0"
            self.queued_downloads_text.value = "0"
            self.completed_downloads_text.value = "0"

    def _refresh_storage(self):
        """Updates storage usage pie chart."""
        try:
            total, used, free = shutil.disk_usage(".")
            # Avoid division by zero
            percent = used / total if total > 0 else 0

            gb = 1024**3

            # Update Pie Chart
            self.storage_chart.sections = [
                ft.PieChartSection(
                    value=free,
                    color=Theme.Status.SUCCESS,
                    radius=20,
                    title=""
                ),
                 ft.PieChartSection(
                    value=used,
                    color=Theme.ACCENT,
                    radius=20,
                    title=""
                ),
            ]

            self.storage_chart.update()

            # Format values as strings for localization
            self.storage_text.value = LM.get(
                "storage_usage",
                f"{used / gb:.1f}",
                f"{total / gb:.1f}",
                f"{free / gb:.1f}",
            )
        except Exception:
            self.storage_text.value = LM.get("storage_info_unavailable")

    def _refresh_history(self):
        """Updates recent history list."""
        items = HistoryManager.get_history(limit=3)
        self.recent_history_list.controls.clear()

        if not items:
            self.recent_history_list.controls.append(
                ft.Text(
                    LM.get("no_recent_downloads"),
                    italic=True,
                    color=Theme.TEXT_MUTED,
                )
            )
        else:
            for item in items:
                ctrl = HistoryItemControl(
                    item,
                    on_open_folder=self._open_history_folder,
                    on_copy_url=self._copy_history_url,
                    on_delete=lambda x: None,
                )
                self.recent_history_list.controls.append(ctrl)

    def _open_history_folder(self, path: str):
        """Open the download folder for a history item."""
        if path and self.page:
            open_folder(path, self.page)

    def _copy_history_url(self, url: str):
        """Copy the URL for a history item."""
        if url and self.page:
            self.page.set_clipboard(url)
