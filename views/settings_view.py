"""Settings View"""

import flet as ft

from config_manager import ConfigManager
from localization_manager import LocalizationManager as LM
from theme import Theme
from ui_utils import validate_output_template, validate_proxy, validate_rate_limit

from .base_view import BaseView

# pylint: disable=missing-class-docstring, too-many-instance-attributes


class SettingsView(BaseView):
    def __init__(self, config):
        super().__init__(LM.get("settings"), ft.icons.SETTINGS)
        self.config = config

        self.proxy_input = ft.TextField(
            label=LM.get("proxy"),
            value=self.config.get("proxy", ""),
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_CARD,
        )
        self.rate_limit_input = ft.TextField(
            label=LM.get("rate_limit"),
            value=self.config.get("rate_limit", ""),
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_CARD,
        )
        self.output_template_input = ft.TextField(
            label=LM.get("output_template"),
            value=self.config.get("output_template", "%(title)s.%(ext)s"),
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_CARD,
        )

        self.use_aria2c_cb = ft.Checkbox(
            label=LM.get("use_aria2c"),
            value=self.config.get("use_aria2c", False),
            fill_color=Theme.PRIMARY,
        )
        self.gpu_accel_dd = ft.Dropdown(
            label=LM.get("gpu_acceleration"),
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
            label=LM.get("theme_mode"),
            options=[
                ft.dropdown.Option("Dark", LM.get("dark")),
                ft.dropdown.Option("Light", LM.get("light")),
                ft.dropdown.Option("System", LM.get("system")),
            ],
            value=self.config.get("theme_mode", "Dark"),
            border_color=Theme.BORDER,
            border_radius=8,
            bgcolor=Theme.BG_CARD,
            on_change=self._on_theme_change,
        )

        # High Contrast
        self.high_contrast_cb = ft.Checkbox(
            label=LM.get("high_contrast_mode"),
            value=self.config.get("high_contrast", False),
            fill_color=Theme.PRIMARY,
            on_change=self._on_high_contrast_change,
        )

        # Compact Mode
        self.compact_mode_cb = ft.Checkbox(
            label=LM.get("compact_mode"),
            value=self.config.get("compact_mode", False),
            fill_color=Theme.PRIMARY,
        )

        self.save_btn = ft.ElevatedButton(
            LM.get("save_settings"),
            on_click=self.save_settings,
            bgcolor=Theme.PRIMARY,
            color=ft.colors.WHITE,
            style=ft.ButtonStyle(padding=20, shape=ft.RoundedRectangleBorder(radius=8)),
        )

        self.add_control(self.proxy_input)
        self.add_control(self.rate_limit_input)
        self.add_control(self.output_template_input)
        self.add_control(ft.Container(height=20))
        self.add_control(
            ft.Text(
                LM.get("performance"),
                size=18,
                weight=ft.FontWeight.W_600,
                color=Theme.TEXT_PRIMARY,
            )
        )
        self.add_control(self.use_aria2c_cb)
        self.add_control(self.gpu_accel_dd)
        self.add_control(ft.Container(height=20))
        self.add_control(
            ft.Text(
                LM.get("appearance"),
                size=18,
                weight=ft.FontWeight.W_600,
                color=Theme.TEXT_PRIMARY,
            )
        )
        self.add_control(self.theme_mode_dd)
        self.add_control(self.high_contrast_cb)
        self.add_control(self.compact_mode_cb)
        self.add_control(ft.Container(height=1, bgcolor=Theme.BORDER))
        self.add_control(ft.Container(height=20))
        # pylint: disable=unused-argument
        self.add_control(self.save_btn)

    # pylint: disable=unused-argument
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

    def _on_high_contrast_change(self, e):
        if self.page:
            self.page.theme = (
                Theme.get_high_contrast_theme()
                if e.control.value
                else Theme.get_theme()
            )

            # Also re-apply theme mode
            mode = self.theme_mode_dd.value
            if mode == "Dark":
                self.page.theme_mode = ft.ThemeMode.DARK
            elif mode == "Light":
                self.page.theme_mode = ft.ThemeMode.LIGHT
            else:
                self.page.theme_mode = ft.ThemeMode.SYSTEM
            # pylint: disable=missing-function-docstring, unused-argument

            self.page.update()

    # pylint: disable=missing-function-docstring, unused-argument

    def save_settings(self, e):
        # Input Validation
        proxy_val = self.proxy_input.value
        if not validate_proxy(proxy_val):
            if self.page:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text(
                            "Invalid Proxy URL (must be http/https/socks and not local)"
                        ),
                        bgcolor=Theme.Status.ERROR,
                    )
                )
            return

        rate_val = self.rate_limit_input.value
        if not validate_rate_limit(rate_val):
            if self.page:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text("Invalid Rate Limit (e.g. 1.5M, 500K)"),
                        bgcolor=Theme.Status.ERROR,
                    )
                )
            return

        tmpl_val = self.output_template_input.value
        if not validate_output_template(tmpl_val):
            if self.page:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text("Invalid Output Template (must be relative path)"),
                        bgcolor=Theme.Status.ERROR,
                    )
                )
            return

        self.config["proxy"] = proxy_val
        self.config["rate_limit"] = rate_val
        self.config["output_template"] = tmpl_val
        self.config["use_aria2c"] = self.use_aria2c_cb.value
        self.config["gpu_accel"] = self.gpu_accel_dd.value
        self.config["theme_mode"] = self.theme_mode_dd.value
        self.config["high_contrast"] = self.high_contrast_cb.value
        self.config["compact_mode"] = self.compact_mode_cb.value
        ConfigManager.save_config(self.config)
        if self.page:
            self.page.open(ft.SnackBar(content=ft.Text(LM.get("settings_saved"))))
