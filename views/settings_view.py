import flet as ft
from theme import Theme
from .base_view import BaseView
from config_manager import ConfigManager


class SettingsView(BaseView):
    def __init__(self, config):
        super().__init__("Settings", ft.Icons.SETTINGS)
        self.config = config

        self.proxy_input = ft.TextField(
            label="Proxy",
            value=self.config.get("proxy", ""),
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_CARD,
        )
        self.rate_limit_input = ft.TextField(
            label="Rate Limit (e.g. 5M)",
            value=self.config.get("rate_limit", ""),
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_CARD,
        )
        self.output_template_input = ft.TextField(
            label="Output Template",
            value=self.config.get("output_template", "%(title)s.%(ext)s"),
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_CARD,
        )

        self.use_aria2c_cb = ft.Checkbox(
            label="Use Aria2c Accelerator",
            value=self.config.get("use_aria2c", False),
            fill_color=Theme.PRIMARY,
        )
        self.gpu_accel_dd = ft.Dropdown(
            label="GPU Acceleration",
            options=[
                ft.dropdown.Option("None"),
                ft.dropdown.Option("auto"),
                ft.dropdown.Option("cuda"),
                ft.dropdown.Option("vulkan"),
            ],
            value=self.config.get("gpu_accel", "None"),
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_CARD,
        )

        # Theme Toggle
        self.theme_mode_dd = ft.Dropdown(
            label="Theme Mode",
            options=[
                ft.dropdown.Option("Dark"),
                ft.dropdown.Option("Light"),
                ft.dropdown.Option("System"),
            ],
            value=self.config.get("theme_mode", "Dark"),
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_CARD,
            on_change=self._on_theme_change,
        )

        self.save_btn = ft.ElevatedButton(
            "Save Configuration",
            on_click=self.save_settings,
            bgcolor=Theme.PRIMARY,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(padding=20, shape=ft.RoundedRectangleBorder(radius=8)),
        )

        self.add_control(self.proxy_input)
        self.add_control(self.rate_limit_input)
        self.add_control(self.output_template_input)
        self.add_control(ft.Divider(height=20, color=ft.Colors.TRANSPARENT))
        self.add_control(
            ft.Text(
                "Performance",
                size=18,
                weight=ft.FontWeight.W_600,
                color=Theme.TEXT_PRIMARY,
            )
        )
        self.add_control(self.use_aria2c_cb)
        self.add_control(self.gpu_accel_dd)
        self.add_control(ft.Divider(height=20, color=ft.Colors.TRANSPARENT))
        self.add_control(
            ft.Text(
                "Appearance",
                size=18,
                weight=ft.FontWeight.W_600,
                color=Theme.TEXT_PRIMARY,
            )
        )
        self.add_control(self.theme_mode_dd)
        self.add_control(ft.Divider(height=20, color=Theme.BORDER))
        self.add_control(self.save_btn)

    def _on_theme_change(self, e):
        mode = self.theme_mode_dd.value
        if self.page:
            if mode == "Dark":
                self.page.theme_mode = ft.ThemeMode.DARK
            elif mode == "Light":
                self.page.theme_mode = ft.ThemeMode.LIGHT
            else:
                self.page.theme_mode = ft.ThemeMode.SYSTEM
            self.page.update()

    def save_settings(self, e):
        self.config["proxy"] = self.proxy_input.value
        self.config["rate_limit"] = self.rate_limit_input.value
        self.config["output_template"] = self.output_template_input.value
        self.config["use_aria2c"] = self.use_aria2c_cb.value
        self.config["gpu_accel"] = self.gpu_accel_dd.value
        self.config["theme_mode"] = self.theme_mode_dd.value
        ConfigManager.save_config(self.config)
        if self.page:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Settings saved successfully!"))
            )
