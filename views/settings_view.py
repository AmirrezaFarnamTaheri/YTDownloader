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

        # Network Section
        self.proxy_input = ft.TextField(
            label=LM.get("proxy"),
            value=self.config.get("proxy", ""),
            **Theme.get_input_decoration(prefix_icon=ft.icons.VPN_LOCK),
        )
        self.rate_limit_input = ft.TextField(
            label=LM.get("rate_limit"),
            value=self.config.get("rate_limit", ""),
            **Theme.get_input_decoration(prefix_icon=ft.icons.SPEED),
        )
        self.output_template_input = ft.TextField(
            label=LM.get("output_template"),
            value=self.config.get("output_template", "%(title)s.%(ext)s"),
            **Theme.get_input_decoration(prefix_icon=ft.icons.FOLDER_SHARED),
        )

        # Performance Section
        self.use_aria2c_switch = ft.Switch(
            label=LM.get("use_aria2c"),
            value=self.config.get("use_aria2c", False),
            active_color=Theme.Primary.MAIN,
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
            **Theme.get_input_decoration(prefix_icon=ft.icons.MEMORY),
        )

        # Appearance Section
        self.theme_mode_dd = ft.Dropdown(
            label=LM.get("theme_mode"),
            options=[
                ft.dropdown.Option("Dark", LM.get("dark")),
                ft.dropdown.Option("Light", LM.get("light")),
                ft.dropdown.Option("System", LM.get("system")),
            ],
            value=self.config.get("theme_mode", "Dark"),
            on_change=self._on_theme_change,
            **Theme.get_input_decoration(prefix_icon=ft.icons.BRIGHTNESS_6),
        )

        self.high_contrast_switch = ft.Switch(
            label=LM.get("high_contrast_mode"),
            value=self.config.get("high_contrast", False),
            active_color=Theme.Primary.MAIN,
            on_change=self._on_high_contrast_change,
        )

        self.compact_mode_switch = ft.Switch(
            label=LM.get("compact_mode"),
            value=self.config.get("compact_mode", False),
            active_color=Theme.Primary.MAIN,
        )

        self.save_btn = ft.ElevatedButton(
            LM.get("save_settings"),
            on_click=self.save_settings,
            icon=ft.icons.SAVE,
            bgcolor=Theme.Primary.MAIN,
            color=Theme.Text.PRIMARY,
            style=ft.ButtonStyle(padding=20, shape=ft.RoundedRectangleBorder(radius=8)),
            tooltip=LM.get("save_settings_tooltip", "Save all changes"),
        )

        # Layout Construction
        self.content_column = ft.Column(spacing=20, scroll=ft.ScrollMode.AUTO)

        # Helper to create sections
        def create_section(title, controls):
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            title,
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=Theme.Text.PRIMARY,
                        ),
                        ft.Column(controls, spacing=15),
                    ],
                    spacing=15,
                ),
                **Theme.get_card_decoration(),
            )

        # General / Network
        self.content_column.controls.append(
            create_section(
                LM.get("general_settings", "General & Network"),
                [self.proxy_input, self.rate_limit_input, self.output_template_input],
            )
        )

        # Performance
        self.content_column.controls.append(
            create_section(
                LM.get("performance"), [self.use_aria2c_switch, self.gpu_accel_dd]
            )
        )

        # Appearance
        self.content_column.controls.append(
            create_section(
                LM.get("appearance"),
                [
                    self.theme_mode_dd,
                    self.high_contrast_switch,
                    self.compact_mode_switch,
                ],
            )
        )

        # Save Button
        self.content_column.controls.append(
            ft.Container(
                content=self.save_btn,
                alignment=ft.alignment.center_right,
                padding=ft.padding.only(top=10),
            )
        )

        self.add_control(
            ft.Container(content=self.content_column, expand=True, padding=10)
        )

    # pylint: disable=unused-argument
    def _on_theme_change(self, e):
        # Allow calling manually without 'e' to refresh
        mode = self.theme_mode_dd.value
        if self.page:
            if mode == "Dark":
                self.page.theme_mode = ft.ThemeMode.DARK
            elif mode == "Light":
                self.page.theme_mode = ft.ThemeMode.LIGHT
            else:
                self.page.theme_mode = ft.ThemeMode.SYSTEM

            # Auto-save theme preference for better UX
            self.config["theme_mode"] = mode
            ConfigManager.save_config(self.config)
            self.page.update()

    def _on_high_contrast_change(self, e):
        if self.page:
            self.page.theme = (
                Theme.get_high_contrast_theme()
                if e.control.value
                else Theme.get_theme()
            )
            # Re-apply mode
            self._on_theme_change(None)

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
                        content=ft.Text(
                            "Invalid Output Template (must be relative path)"
                        ),
                        bgcolor=Theme.Status.ERROR,
                    )
                )
            return

        self.config["proxy"] = proxy_val
        self.config["rate_limit"] = rate_val
        self.config["output_template"] = tmpl_val
        self.config["use_aria2c"] = self.use_aria2c_switch.value
        self.config["gpu_accel"] = self.gpu_accel_dd.value
        self.config["theme_mode"] = self.theme_mode_dd.value
        self.config["high_contrast"] = self.high_contrast_switch.value
        self.config["compact_mode"] = self.compact_mode_switch.value
        ConfigManager.save_config(self.config)
        if self.page:
            self.page.open(ft.SnackBar(content=ft.Text(LM.get("settings_saved"))))
