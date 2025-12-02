import flet as ft

from history_manager import HistoryManager
from localization_manager import LocalizationManager as LM
from theme import Theme

from .base_view import BaseView


class DashboardView(BaseView):
    def __init__(self):
        super().__init__(LM.get("dashboard"), ft.Icons.DASHBOARD)
        self.stats_row = ft.Row(wrap=True, spacing=20)
        self.add_control(self.stats_row)
        self.add_control(ft.Divider(color=ft.Colors.TRANSPARENT, height=20))
        self.add_control(
            ft.Text(
                LM.get("recent_activity"),
                size=20,
                weight=ft.FontWeight.BOLD,
                color=Theme.TEXT_PRIMARY,
            )
        )

    def load(self):
        self.stats_row.controls.clear()
        history = HistoryManager.get_history(limit=1000)
        total_downloads = len(history)

        card = self._create_stat_card(
            LM.get("total_downloads"),
            str(total_downloads),
            ft.Icons.DOWNLOAD_DONE,
            Theme.PRIMARY,
        )
        self.stats_row.controls.append(card)
        self.update()

    def _create_stat_card(self, title, value, icon, color):
        return ft.Container(
            padding=20,
            bgcolor=Theme.BG_CARD,
            border_radius=12,
            width=240,
            height=140,
            border=ft.border.all(1, Theme.BORDER),
            content=ft.Column(
                [
                    ft.Icon(icon, size=40, color=color),
                    ft.Text(
                        value,
                        size=36,
                        weight=ft.FontWeight.BOLD,
                        color=Theme.TEXT_PRIMARY,
                    ),
                    ft.Text(title, color=Theme.TEXT_SECONDARY),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )
