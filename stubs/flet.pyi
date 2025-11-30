from typing import Any

class Page:
    title: str
    theme_mode: Any
    padding: int
    window_min_width: int
    window_min_height: int
    bgcolor: str
    theme: Any
    overlay: list[Any]
    on_disconnect: Any
    on_close: Any
    def open(self, control: Any) -> None: ...
    def update(self) -> None: ...
    def add(self, *controls: Any) -> None: ...
    def clean(self) -> None: ...
    def window_destroy(self) -> None: ...

class Control: ...

class Container(Control):
    def __init__(
        self,
        content: Any = None,
        expand: Any = None,
        bgcolor: Any = None,
        alignment: Any = None,
        padding: Any = None,
        border_radius: Any = None,
        width: Any = None,
        height: Any = None,
        border: Any = None,
    ): ...

class Column(Control):
    controls: list[Control]
    def __init__(
        self,
        controls: Any = None,
        expand: Any = None,
        spacing: Any = None,
        alignment: Any = None,
        horizontal_alignment: Any = None,
        scroll: Any = None,
        width: Any = None,
    ): ...

class Row(Control):
    controls: list[Control]
    def __init__(
        self,
        controls: Any = None,
        expand: Any = None,
        spacing: Any = None,
        alignment: Any = None,
        vertical_alignment: Any = None,
    ): ...

class Text(Control):
    def __init__(
        self,
        value: Any = None,
        size: Any = None,
        weight: Any = None,
        color: Any = None,
        overflow: Any = None,
        max_lines: Any = None,
        text_align: Any = None,
    ): ...

class Icon(Control):
    def __init__(self, name: Any = None, size: Any = None, color: Any = None): ...

class ProgressBar(Control):
    def __init__(
        self,
        value: Any = None,
        color: Any = None,
        bgcolor: Any = None,
        width: Any = None,
        height: Any = None,
        border_radius: Any = None,
    ): ...

class SnackBar(Control):
    def __init__(self, content: Any = None): ...

class FilePicker(Control):
    on_result: Any
    def pick_files(
        self, allow_multiple: bool = False, allowed_extensions: Any = None
    ): ...

class FilePickerResultEvent:
    files: list[Any]

class TimePicker(Control):
    on_change: Any
    def __init__(
        self,
        confirm_text: Any = None,
        error_invalid_text: Any = None,
        help_text: Any = None,
    ): ...

class NavigationRail(Control):
    def __init__(
        self,
        selected_index: Any = None,
        label_type: Any = None,
        on_change: Any = None,
        destinations: Any = None,
        bgcolor: Any = None,
        extended: bool = False,
        min_width: Any = None,
        min_extended_width: Any = None,
        group_alignment: Any = None,
    ): ...

class NavigationRailDestination(Control):
    def __init__(
        self, icon: Any = None, selected_icon: Any = None, label: Any = None
    ): ...

class VerticalDivider(Control):
    def __init__(self, width: Any = None, thickness: Any = None, color: Any = None): ...

class Switch(Control):
    def __init__(
        self,
        label: Any = None,
        value: bool = False,
        on_change: Any = None,
        active_color: Any = None,
    ): ...

class IconButton(Control):
    def __init__(
        self,
        icon: Any = None,
        on_click: Any = None,
        tooltip: Any = None,
        icon_color: Any = None,
    ): ...

class Divider(Control):
    def __init__(
        self, height: Any = None, thickness: Any = None, color: Any = None
    ): ...

class Image(Control):
    def __init__(
        self, src: Any = None, width: Any = None, height: Any = None, color: Any = None
    ): ...

class LinearGradient:
    def __init__(self, begin: Any = None, end: Any = None, colors: Any = None): ...

class BorderSide:
    def __init__(self, width: Any = None, color: Any = None): ...

# Relaxed types
Colors: Any
Icons: Any
FontWeight: Any
ThemeMode: Any
MainAxisAlignment: Any
CrossAxisAlignment: Any
TextOverflow: Any
NavigationRailLabelType: Any
alignment: Any
WEB_BROWSER: Any
padding: Any
border: Any
LabelPosition: Any

def app(target: Any = None, view: Any = None, port: Any = None): ...

# Classes for Theme
class Theme:
    def __init__(
        self,
        color_scheme: Any = None,
        visual_density: Any = None,
        page_transitions: Any = None,
    ): ...

class ColorScheme:
    def __init__(
        self,
        primary: Any = None,
        secondary: Any = None,
        background: Any = None,
        surface: Any = None,
        error: Any = None,
        on_primary: Any = None,
        on_secondary: Any = None,
        on_background: Any = None,
        on_surface: Any = None,
        surface_tint: Any = None,
        outline: Any = None,
    ): ...

class VisualDensity:
    COMFORTABLE: Any

class PageTransitionsTheme:
    def __init__(
        self,
        android: Any = None,
        ios: Any = None,
        macos: Any = None,
        linux: Any = None,
        windows: Any = None,
    ): ...

class PageTransitionTheme:
    ZOOM: Any
    CUPERTINO: Any
