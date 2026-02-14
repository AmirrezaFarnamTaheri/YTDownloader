"""
Dashboard View Module.

Features a modern dashboard with system status, quick actions,
active download summaries, and recent history.
Refactored to use charts, health indicators, and richer quick actions.
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
    - Activity history (BarChart)
    - System health chips (FFmpeg, sync, concurrency, cache)
    - Recent download history
    """

    def __init__(
        self,
        on_navigate: Callable[[int], None],
        on_paste_url: Callable[[], None],
        on_batch_import: Callable[[], None],
        queue_manager,
    ):
        super().__init__(LM.get("dashboard"), ft.icons.DASHBOARD_ROUNDED)
        self.on_navigate = on_navigate
        self.on_paste_url = on_paste_url
        self.on_batch_import = on_batch_import
        self.queue_manager = queue_manager

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

        self.activity_chart = ft.BarChart(
            bar_groups=[],
            border=ft.border.all(1, Theme.BORDER),
            left_axis=ft.ChartAxis(labels_size=40, title=ft.Text("Downloads", size=10)),
            bottom_axis=ft.ChartAxis(labels_size=40, title=ft.Text("Day", size=10)),
            horizontal_grid_lines=ft.ChartGridLines(
                color=Theme.BORDER, width=1, dash_pattern=[3, 3]
            ),
            tooltip_bgcolor=Theme.BG_CARD,
            max_y=10,  # Dynamic
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
        self.failed_downloads_text = ft.Text(
            "0", size=32, weight=ft.FontWeight.BOLD, color=Theme.Status.ERROR
        )
        self.success_rate_text = ft.Text(
            "100%",
            size=14,
            weight=ft.FontWeight.W_600,
            color=Theme.Text.SECONDARY,
        )
        self.health_chips_row = ft.Row(spacing=8, wrap=True)

        self.refresh_btn = ft.IconButton(
            ft.icons.REFRESH_ROUNDED,
            tooltip=LM.get("refresh_dashboard", "Refresh"),
            on_click=lambda _: self.load(),
            icon_color=Theme.Text.SECONDARY,
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
                    # System Health
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    LM.get("system_health", "System Health"),
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=Theme.Text.PRIMARY,
                                ),
                                self.health_chips_row,
                            ],
                            spacing=12,
                        ),
                        **Theme.get_card_decoration(),
                    ),
                    ft.Container(height=20),
                    # Charts Row
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        LM.get("system_status"),
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [self.storage_chart, self.storage_text],
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        ),
                                        **Theme.get_card_decoration(),
                                        width=300,
                                        # Removed explicit padding=20 here to avoid collision with get_card_decoration
                                    ),
                                ]
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Activity (Last 7 Days)",
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Container(
                                        content=self.activity_chart,
                                        **Theme.get_card_decoration(),
                                        width=400,
                                        height=230,
                                        # Removed explicit padding=20 here too
                                    ),
                                ],
                                expand=True,
                            ),
                        ],
                        wrap=True,
                        alignment=ft.MainAxisAlignment.START,
                        spacing=20,
                    ),
                    ft.Container(height=20),
                    # Recent History
                    ft.Row(
                        [
                            ft.Text(
                                LM.get("recent_history", "Recent History"),
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=Theme.Text.PRIMARY,
                            ),
                            self.refresh_btn,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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
                quick_btn(
                    ft.icons.FOLDER_OPEN_ROUNDED,
                    LM.get("open_downloads_folder"),
                    lambda _: self._open_downloads_root(),
                    Theme.Primary.MAIN,
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
                        stat_card(
                            LM.get("failed", "Failed"),
                            self.failed_downloads_text,
                            ft.icons.ERROR_OUTLINE,
                            Theme.Status.ERROR,
                        ),
                    ],
                    spacing=15,
                    wrap=True,
                ),
                ft.Row(
                    [
                        ft.Text(
                            LM.get("success_rate", "Success Rate"),
                            size=12,
                            color=Theme.Text.SECONDARY,
                        ),
                        self.success_rate_text,
                    ],
                    spacing=10,
                ),
            ],
            spacing=10,
        )

    def load(self):
        """Refreshes the dashboard data."""
        self._refresh_storage()
        self._refresh_stats()
        self._refresh_history()
        self._refresh_activity()  # New
        self._refresh_health()
        if self.page:
            self.update()

    def _refresh_activity(self):
        """
        Refresh activity chart using real data from HistoryManager.
        """
        try:
            from app_state import state  # local import to avoid circulars

            hm = getattr(state, "history_manager", None) or HistoryManager()
            activity_data = hm.get_download_activity(days=7)
        except Exception:  # pylint: disable=broad-exception-caught
            activity_data = []

        groups = []
        labels = []

        max_count = 0

        for i, day in enumerate(activity_data):
            count = day.get("count", 0)
            max_count = max(max_count, count)

            groups.append(
                ft.BarChartGroup(
                    x=i,
                    bar_rods=[
                        ft.BarChartRod(
                            from_y=0,
                            to_y=count,
                            color=Theme.Primary.MAIN,
                            width=15,
                            border_radius=4,
                            tooltip=f"{day.get('date')}: {count}",
                        )
                    ],
                )
            )
            labels.append(
                ft.ChartAxisLabel(value=i, label=ft.Text(day.get("label", ""), size=10))
            )

        self.activity_chart.bar_groups = groups
        self.activity_chart.bottom_axis.labels = labels
        # Adjust Y axis max to fit data + buffer, min 5
        self.activity_chart.max_y = max(max_count + 2, 5)
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
                    "queued": sum(
                        1
                        for i in items
                        if i.get("status") == "Queued"
                        or i.get("status") == "Allocating"
                    ),
                    "completed": sum(
                        1 for i in items if i.get("status") == "Completed"
                    ),
                }

            self.active_downloads_text.value = str(stats.get("downloading", 0))
            self.queued_downloads_text.value = str(stats.get("queued", 0))
            self.completed_downloads_text.value = str(stats.get("completed", 0))
            failed = stats.get("failed", 0)
            self.failed_downloads_text.value = str(failed)
            done_count = stats.get("completed", 0) + failed
            success_rate = (
                (stats.get("completed", 0) / done_count * 100) if done_count else 100
            )
            self.success_rate_text.value = f"{success_rate:.0f}%"

        except Exception as e:
            logger.debug("Error refreshing stats: %s", e)
            self.active_downloads_text.value = "0"
            self.queued_downloads_text.value = "0"
            self.completed_downloads_text.value = "0"
            self.failed_downloads_text.value = "0"
            self.success_rate_text.value = "100%"

    def _refresh_storage(self):
        """Updates storage usage pie chart."""
        try:
            total, used, free = shutil.disk_usage(".")
            gb = 1024**3

            # Update Pie Chart
            self.storage_chart.sections = [
                ft.PieChartSection(
                    value=free, color=Theme.Status.SUCCESS, radius=20, title=""
                ),
                ft.PieChartSection(value=used, color=Theme.ACCENT, radius=20, title=""),
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
        try:
            # pylint: disable=import-outside-toplevel
            from app_state import state

            hm = getattr(state, "history_manager", None) or HistoryManager()
            items = hm.get_history(limit=3)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to load history: %s", e)
            items = []

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

    def _open_downloads_root(self):
        """Open the default downloads folder."""
        try:
            from app_state import state
            from ui_utils import get_default_download_path

            root = get_default_download_path(state.config.get("download_path"))
            if self.page:
                open_folder(root, self.page)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("Failed to open downloads root: %s", exc)

    @staticmethod
    def _build_health_chip(label: str, value: str, color: str) -> ft.Container:
        """Build a small health chip used in the dashboard system-health row."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=8, height=8, border_radius=4, bgcolor=color),
                    ft.Text(label, size=12, color=Theme.Text.SECONDARY),
                    ft.Text(
                        value,
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=Theme.Text.PRIMARY,
                    ),
                ],
                spacing=8,
                tight=True,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor=ft.colors.with_opacity(0.22, Theme.BG_HOVER),
            border=ft.border.all(1, Theme.BORDER),
            border_radius=999,
        )

    def _refresh_health(self) -> None:
        """Refresh runtime health chips (ffmpeg, sync, concurrency, cache)."""
        try:
            from app_state import state

            total, _, free = shutil.disk_usage(".")
            free_pct = int((free / total) * 100) if total else 0
            sync_enabled = bool(state.config.get("auto_sync_enabled", False))
            ffmpeg_status = state.ffmpeg_available
            concurrency = str(state.config.get("max_concurrent_downloads", 3))
            cache_size = str(state.config.get("metadata_cache_size", 50))

            self.health_chips_row.controls = [
                self._build_health_chip(
                    LM.get("ffmpeg", "FFmpeg"),
                    (
                        LM.get("ready", "Ready")
                        if ffmpeg_status
                        else LM.get("missing", "Missing")
                    ),
                    Theme.Status.SUCCESS if ffmpeg_status else Theme.Status.ERROR,
                ),
                self._build_health_chip(
                    LM.get("sync", "Sync"),
                    (
                        LM.get("enabled", "Enabled")
                        if sync_enabled
                        else LM.get("disabled", "Disabled")
                    ),
                    Theme.Status.INFO if sync_enabled else Theme.Text.SECONDARY,
                ),
                self._build_health_chip(
                    LM.get("concurrency", "Concurrency"),
                    concurrency,
                    Theme.ACCENT,
                ),
                self._build_health_chip(
                    LM.get("metadata_cache", "Metadata Cache"),
                    cache_size,
                    Theme.ACCENT_SECONDARY,
                ),
                self._build_health_chip(
                    LM.get("disk_free", "Disk Free"),
                    f"{free_pct}%",
                    Theme.Status.SUCCESS if free_pct >= 20 else Theme.Status.WARNING,
                ),
            ]
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("Failed to refresh health chips: %s", exc)
            self.health_chips_row.controls = []
