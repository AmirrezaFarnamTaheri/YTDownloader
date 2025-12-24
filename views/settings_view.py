"""Settings View"""

import logging

import flet as ft

from config_manager import ConfigManager
from localization_manager import LocalizationManager as LM
from theme import Theme
from ui_utils import (
    validate_download_path,
    validate_output_template,
    validate_proxy,
    validate_rate_limit,
)

from .base_view import BaseView

# pylint: disable=missing-class-docstring, too-many-instance-attributes


class SettingsView(BaseView):
    def __init__(self, config):
        super().__init__(LM.get("settings"), ft.icons.SETTINGS)
        self.config = config
        self.logger = logging.getLogger(__name__)

        # General / Network Section
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
        self.download_path_input = ft.TextField(
            label=LM.get("download_path"),
            value=self.config.get("download_path", ""),
            **Theme.get_input_decoration(
                prefix_icon=ft.icons.FOLDER,
                hint_text=LM.get("download_path_hint"),
            ),
        )

        language_names = {
            "en": LM.get("language_name_en"),
            "es": LM.get("language_name_es"),
            "fa": LM.get("language_name_fa"),
        }
        available_langs = LM.get_available_languages()
        self.language_dd = ft.Dropdown(
            label=LM.get("language"),
            options=[
                ft.dropdown.Option(code, language_names.get(code, code))
                for code in available_langs
            ],
            value=self.config.get("language", "en"),
            **Theme.get_input_decoration(prefix_icon=ft.icons.LANGUAGE),
        )

        self.max_concurrent_input = ft.TextField(
            label=LM.get("max_concurrent_downloads"),
            value=str(self.config.get("max_concurrent_downloads", 3)),
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(allow=r"\\d+"),
            **Theme.get_input_decoration(prefix_icon=ft.icons.FILTER_3),
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
                ft.dropdown.Option("None", LM.get("none")),
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
            value=self.config.get("theme_mode", "System"),
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

        # General
        self.content_column.controls.append(
            create_section(
                LM.get("general_settings"),
                [
                    self.download_path_input,
                    self.output_template_input,
                    self.language_dd,
                    self.max_concurrent_input,
                ],
            )
        )

        # Network
        self.content_column.controls.append(
            create_section(
                LM.get("network_settings"),
                [self.proxy_input, self.rate_limit_input],
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
        download_path_val = self.download_path_input.value
        if not validate_download_path(download_path_val):
            if self.page:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text(LM.get("invalid_download_path")),
                        bgcolor=Theme.Status.ERROR,
                    )
                )
            return

        proxy_val = self.proxy_input.value
        if not validate_proxy(proxy_val):
            if self.page:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text(LM.get("invalid_proxy")),
                        bgcolor=Theme.Status.ERROR,
                    )
                )
            return

        rate_val = self.rate_limit_input.value
        if not validate_rate_limit(rate_val):
            if self.page:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text(LM.get("invalid_rate_limit")),
                        bgcolor=Theme.Status.ERROR,
                    )
                )
            return

        tmpl_val = self.output_template_input.value
        if not validate_output_template(tmpl_val):
            if self.page:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text(LM.get("invalid_output_template")),
                        bgcolor=Theme.Status.ERROR,
                    )
                )
            return

        max_concurrent_raw = self.max_concurrent_input.value
        try:
            max_concurrent = int(max_concurrent_raw)
            if max_concurrent < 1:
                raise ValueError
        except Exception:  # pylint: disable=broad-exception-caught
            if self.page:
                self.page.open(
                    ft.SnackBar(
                        content=ft.Text(LM.get("invalid_max_concurrent_downloads")),
                        bgcolor=Theme.Status.ERROR,
                    )
                )
            return

        language_before = self.config.get("language")
        language_after = self.language_dd.value

        self.config["download_path"] = download_path_val
        self.config["proxy"] = proxy_val
        self.config["rate_limit"] = rate_val
        self.config["output_template"] = tmpl_val
        self.config["use_aria2c"] = self.use_aria2c_switch.value
        self.config["gpu_accel"] = self.gpu_accel_dd.value
        self.config["theme_mode"] = self.theme_mode_dd.value
        self.config["high_contrast"] = self.high_contrast_switch.value
        self.config["compact_mode"] = self.compact_mode_switch.value
        self.config["language"] = language_after
        self.config["max_concurrent_downloads"] = max_concurrent
        ConfigManager.save_config(self.config)
        self.logger.info(
            "Settings saved (language=%s, max_concurrent=%s)",
            language_after,
            max_concurrent,
        )

        concurrency_applied = True
        try:
            # pylint: disable=import-outside-toplevel
            from tasks import configure_concurrency

            concurrency_applied = configure_concurrency(max_concurrent)
        except Exception:
            concurrency_applied = False

        messages = [LM.get("settings_saved")]
        if language_before != language_after:
            LM.load_language(language_after)
            if self.page:
                new_title = LM.get("app_title")
                if new_title and new_title != "app_title":
                    self.page.title = new_title
            messages.append(LM.get("language_restart_required"))
        if not concurrency_applied:
            messages.append(LM.get("concurrency_update_deferred"))

        if self.page:
            self.page.open(ft.SnackBar(content=ft.Text(" ".join(messages))))
