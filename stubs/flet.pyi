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
    def open(self, control: Any) -> None: ...
    def update(self) -> None: ...
    def add(self, *controls: Any) -> None: ...
    def clean(self) -> None: ...

class Control: ...
class Container(Control):
    def __init__(self, content: Any = None, expand: Any = None, bgcolor: str = None, alignment: Any = None, padding: Any = None, border_radius: Any = None, width: Any = None, height: Any = None): ...
class Column(Control):
    controls: list[Control]
    def __init__(self, controls: list[Control] = None, expand: Any = None, spacing: Any = None, alignment: Any = None, horizontal_alignment: Any = None, scroll: Any = None): ...
class Row(Control):
    controls: list[Control]
    def __init__(self, controls: list[Control] = None, expand: Any = None, spacing: Any = None, alignment: Any = None, vertical_alignment: Any = None): ...
class Text(Control):
    def __init__(self, value: str = None, size: int = None, weight: Any = None, color: str = None, overflow: Any = None, max_lines: int = None, text_align: Any = None): ...
class Icon(Control):
    def __init__(self, name: str = None, size: int = None, color: str = None): ...
class ProgressBar(Control):
    def __init__(self, value: float = None, color: str = None, bgcolor: str = None, width: int = None, height: int = None, border_radius: Any = None): ...
class SnackBar(Control):
    def __init__(self, content: Any = None): ...
class FilePicker(Control):
    on_result: Any
    def pick_files(self, allow_multiple: bool = False, allowed_extensions: list[str] = None): ...
class FilePickerResultEvent:
    files: list[Any]
class TimePicker(Control):
    on_change: Any
    def __init__(self, confirm_text: str = None, error_invalid_text: str = None, help_text: str = None): ...
class NavigationRail(Control):
    def __init__(self, selected_index: int = None, label_type: Any = None, on_change: Any = None, destinations: list[Any] = None, bgcolor: str = None, extended: bool = False, min_width: int = None, min_extended_width: int = None): ...
class NavigationRailDestination(Control):
    def __init__(self, icon: str = None, selected_icon: str = None, label: str = None): ...
class VerticalDivider(Control):
    def __init__(self, width: int = None, thickness: int = None, color: str = None): ...
class Switch(Control):
    def __init__(self, label: str = None, value: bool = False, on_change: Any = None): ...
class IconButton(Control):
    def __init__(self, icon: str = None, on_click: Any = None, tooltip: str = None): ...
class Divider(Control):
    def __init__(self, height: int = None, thickness: int = None, color: str = None): ...
class Colors:
    BLUE: str
    RED: str
    GREEN: str
    GREY_800: str
    GREY_900: str
class Icons:
    DOWNLOAD: str
    HISTORY: str
    DASHBOARD: str
    RSS_FEED: str
    SETTINGS: str
    VIDEO_LIBRARY: str
    MENU: str
    CLOSE: str
    FOLDER_OPEN: str
    REFRESH: str
    DELETE: str
    PLAY_ARROW: str
    STOP: str
    ERROR: str
    WARNING: str
    CHECK: str
class FontWeight:
    BOLD: str
    W_600: str
class ThemeMode:
    DARK: Any
class MainAxisAlignment:
    START: Any
    CENTER: Any
    END: Any
    SPACE_BETWEEN: Any
class CrossAxisAlignment:
    START: Any
    CENTER: Any
    END: Any
class TextOverflow:
    ELLIPSIS: Any
class NavigationRailLabelType:
    ALL: Any
class LinearGradient:
    def __init__(self, begin: Any = None, end: Any = None, colors: list[str] = None): ...
class alignment:
    center: Any
    top_center: Any
    bottom_center: Any
WEB_BROWSER: Any
def app(target: Any = None, view: Any = None, port: int = None): ...
