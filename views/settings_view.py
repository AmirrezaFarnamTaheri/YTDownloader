"""
Settings View module.
"""

import logging
from collections.abc import Callable

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
from views.base_view import BaseView

# pylint: disable=missing-class-docstring, too-many-instance-attributes


class SettingsView(BaseView):
    _THEME_CHOICES = ("System", "Light", "Dark", "High Contrast")

    def __init__(
        self,
        config,
        on_toggle_clipboard: Callable[..., None] | None = None,
        on_compact_mode_change=None,
    ):
        super().__init__(LM.get("settings"), ft.icons.SETTINGS_ROUNDED)
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.on_toggle_clipboard = on_toggle_clipboard
        self.on_compact_mode_change = on_compact_mode_change
        stored_theme_mode = str(self.config.get("theme_mode", "System"))
        if self.config.get("high_contrast", False) or stored_theme_mode.lower() in {
            "high contrast",
            "high_contrast",
            "high-contrast",
        }:
            initial_theme_mode = "High Contrast"
        else:
            initial_theme_mode = (
                stored_theme_mode
                if stored_theme_mode in self._THEME_CHOICES
                else "System"
            )

        # --- Controls ---
        # General Section
        self.download_path_input = ft.TextField(
            label=LM.get("download_path"),
            value=self.config.get("download_path", "downloads"),
            expand=True,
            **Theme.get_input_decoration(prefix_icon=ft.icons.FOLDER_OPEN_ROUNDED),
        )

        self.output_template_input = ft.TextField(
            label=LM.get("output_template"),
            value=self.config.get("output_template", "%(title)s.%(ext)s"),
            expand=True,
            **Theme.get_input_decoration(prefix_icon=ft.icons.TEXT_FIELDS_ROUNDED),
        )

        self.language_dd = ft.Dropdown(
            label=LM.get("language"),
            options=[
                ft.dropdown.Option("en", "English"),
                ft.dropdown.Option("es", "Español"),
                ft.dropdown.Option("fa", "فارسی"),
            ],
            value=self.config.get("language", "en"),
            **Theme.get_input_decoration(prefix_icon=ft.icons.LANGUAGE_ROUNDED),
        )

        self.max_concurrent_input = ft.TextField(
            label=LM.get("max_concurrent_downloads"),
            value=str(self.config.get("max_concurrent_downloads", 3)),
            keyboard_type=ft.KeyboardType.NUMBER,
            **Theme.get_input_decoration(prefix_icon=ft.icons.SPEED_ROUNDED),
        )

        self.clipboard_monitor_switch = ft.Switch(
            label=LM.get("clipboard_monitor"),
            value=self.config.get("clipboard_monitor_enabled", False),
            active_color=Theme.Primary.MAIN,
        )

        # Network Section
        self.proxy_input = ft.TextField(
            label=LM.get("proxy_url"),
            value=self.config.get("proxy", ""),
            **Theme.get_input_decoration(
                hint_text="http://user:pass@host:port",
                prefix_icon=ft.icons.SECURITY_ROUNDED,
            ),
        )

        self.rate_limit_input = ft.TextField(
            label=LM.get("rate_limit"),
            value=self.config.get("rate_limit", ""),
            **Theme.get_input_decoration(
                hint_text="e.g. 5M, 100K", prefix_icon=ft.icons.NETWORK_CHECK_ROUNDED
            ),
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
            **Theme.get_input_decoration(prefix_icon=ft.icons.MEMORY_ROUNDED),
        )

        # Appearance Section
        self.theme_mode_dd = ft.Dropdown(
            label=LM.get("theme_mode"),
            options=[
                ft.dropdown.Option("System", LM.get("system")),
                ft.dropdown.Option("Light", LM.get("light")),
                ft.dropdown.Option("Dark", LM.get("dark")),
                ft.dropdown.Option("High Contrast", LM.get("high_contrast_mode")),
            ],
            value=initial_theme_mode,
            on_change=self._on_theme_change,
            **Theme.get_input_decoration(prefix_icon=ft.icons.BRIGHTNESS_6_ROUNDED),
        )

        self.compact_mode_switch = ft.Switch(
            label=LM.get("compact_mode"),
            value=self.config.get("compact_mode", False),
            active_color=Theme.Primary.MAIN,
            on_change=self._on_compact_mode_change,
        )

        self.save_btn = ft.ElevatedButton(
            LM.get("save_settings"),
            on_click=self.save_settings,
            icon=ft.icons.SAVE_ROUNDED,
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
                    self.clipboard_monitor_switch,
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
        mode = self.theme_mode_dd.value or "System"
        is_high_contrast = mode == "High Contrast"
        if self.page:
            if is_high_contrast:
                self.page.theme = Theme.get_high_contrast_theme()
                self.page.theme_mode = ft.ThemeMode.SYSTEM
            else:
                self.page.theme = Theme.get_theme()
                if mode == "Dark":
                    self.page.theme_mode = ft.ThemeMode.DARK
                elif mode == "Light":
                    self.page.theme_mode = ft.ThemeMode.LIGHT
                else:
                    self.page.theme_mode = ft.ThemeMode.SYSTEM

            # Auto-save theme preference for better UX.
            # Keep "High Contrast" in theme_mode for backward compatibility and tests.
            self.config["theme_mode"] = "High Contrast" if is_high_contrast else mode
            self.config["high_contrast"] = is_high_contrast
            try:
                ConfigManager.save_config(self.config)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.logger.error("Failed to persist theme settings: %s", exc)
            self.page.update()

    def _on_compact_mode_change(self, e):
        # Auto-save compact_mode preference
        self.config["compact_mode"] = e.control.value
        ConfigManager.save_config(self.config)
        if self.on_compact_mode_change:
            self.on_compact_mode_change(e.control.value)

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
        clipboard_before = self.config.get("clipboard_monitor_enabled", False)
        language_after = self.language_dd.value

        self.config["download_path"] = download_path_val
        self.config["proxy"] = proxy_val
        self.config["rate_limit"] = rate_val
        self.config["output_template"] = tmpl_val
        self.config["use_aria2c"] = self.use_aria2c_switch.value
        self.config["gpu_accel"] = self.gpu_accel_dd.value
        selected_theme = self.theme_mode_dd.value or "System"
        is_high_contrast = selected_theme == "High Contrast"
        self.config["theme_mode"] = (
            "High Contrast" if is_high_contrast else selected_theme
        )
        self.config["high_contrast"] = is_high_contrast
        self.config["compact_mode"] = self.compact_mode_switch.value
        self.config["language"] = language_after
        self.config["max_concurrent_downloads"] = max_concurrent
        clipboard_after = bool(self.clipboard_monitor_switch.value)
        self.config["clipboard_monitor_enabled"] = clipboard_after
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
        if clipboard_before != clipboard_after:
            if self.on_toggle_clipboard:
                try:
                    self.on_toggle_clipboard(clipboard_after, show_message=False)
                except TypeError:
                    # Backwards compatibility with older callback signatures
                    self.on_toggle_clipboard(clipboard_after)
            messages.append(
                LM.get(
                    "clipboard_monitor_enabled"
                    if clipboard_after
                    else "clipboard_monitor_disabled"
                )
            )
        if not concurrency_applied:
            messages.append(LM.get("concurrency_update_deferred"))

        if self.page:
            self.page.open(ft.SnackBar(content=ft.Text(" ".join(messages))))
