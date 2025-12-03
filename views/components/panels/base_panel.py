"""
Base class for download panels.
"""

from typing import Any, Callable, Dict, Optional

import flet as ft

from theme import Theme


class BasePanel(ft.Container):
    """
    Abstract base panel for platform-specific download options.
    """

    def __init__(self, info: Dict[str, Any], on_option_change: Callable):
        super().__init__()
        self.info = info
        self.on_option_change = on_option_change
        self.padding = 10
        self.border_radius = 8
        self.bgcolor = Theme.Surface.CARD
        # self.border = ft.border.all(1, Theme.Divider.COLOR) # Optional border

    def build(self):
        """Build the panel content. Should be overridden."""
        return ft.Column([])

    def get_options(self) -> Dict[str, Any]:
        """Return the selected options. Should be overridden."""
        return {}
