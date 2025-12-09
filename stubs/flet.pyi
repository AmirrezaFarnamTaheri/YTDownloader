# pylint: disable=all
# pylint: disable=all
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
    navigation_bar: Any
    on_resized: Any
    on_keyboard_event: Any
    def open(self, control: Any) -> None: ...
    def update(self) -> None: ...
    def add(self, *controls: Any) -> None: ...
    def clean(self) -> None: ...
    def window_destroy(self) -> None: ...

class Control:
    visible: bool
    disabled: bool
    width: Any
    height: Any
    expand: Any
    opacity: Any
    tooltip: Any
    data: Any
    def update(self) -> None: ...

class Container(Control):
    content: Any
    padding: Any
    border: Any
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
        on_click: Any = None,
        ink: bool = False,
        visible: bool = True,
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
        wrap: bool = False,
        run_spacing: Any = None,
    ): ...

class Text(Control):
    value: str
    color: Any
    def __init__(
        self,
        value: Any = None,
        size: Any = None,
        weight: Any = None,
        color: Any = None,
        overflow: Any = None,
        max_lines: Any = None,
        text_align: Any = None,
        selectable: bool = False,
        no_wrap: bool = False,
        font_family: Any = None,
        style: Any = None,
        theme_style: Any = None,
        visible: bool = True,
    ): ...

class Icon(Control):
    def __init__(self, name: Any = None, size: Any = None, color: Any = None): ...

class ProgressBar(Control):
    value: Any
    color: Any
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
    def __init__(
        self,
        content: Any = None,
        action: Any = None,
        on_action: Any = None,
        bgcolor: Any = None,
        open: bool = False,
    ): ...

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
    extended: bool
    min_width: Any
    min_extended_width: Any
    label_type: Any
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

class NavigationBar(Control):
    def __init__(
        self,
        destinations: Any = None,
        selected_index: int = 0,
        bgcolor: Any = None,
        on_change: Any = None,
        height: Any = None,
        visible: bool = True,
    ): ...

class NavigationBarDestination(Control):
    def __init__(
        self,
        icon: Any = None,
        selected_icon: Any = None,
        label: Any = None,
    ): ...

class VerticalDivider(Control):
    def __init__(self, width: Any = None, thickness: Any = None, color: Any = None): ...

class Switch(Control):
    label: str
    value: bool
    def __init__(
        self,
        label: Any = None,
        value: bool = False,
        on_change: Any = None,
        active_color: Any = None,
        tooltip: Any = None,
    ): ...

class IconButton(Control):
    def __init__(
        self,
        icon: Any = None,
        on_click: Any = None,
        tooltip: Any = None,
        icon_color: Any = None,
        icon_size: Any = None,
        style: Any = None,
    ): ...

class Divider(Control):
    def __init__(
        self, height: Any = None, thickness: Any = None, color: Any = None
    ): ...

class Image(Control):
    src: str
    def __init__(
        self,
        src: Any = None,
        width: Any = None,
        height: Any = None,
        color: Any = None,
        fit: Any = None,
        border_radius: Any = None,
    ): ...

class LinearGradient:
    def __init__(self, begin: Any = None, end: Any = None, colors: Any = None): ...

class BorderSide:
    def __init__(self, width: Any = None, color: Any = None): ...

class TextField(Control):
    value: str
    def __init__(
        self,
        label: Any = None,
        value: Any = None,
        text_align: Any = None,
        width: Any = None,
        height: Any = None,
        multiline: bool = False,
        read_only: bool = False,
        on_change: Any = None,
        on_submit: Any = None,
        password: bool = False,
        can_reveal_password: bool = False,
        keyboard_type: Any = None,
        border: Any = None,
        filled: bool = False,
        hint_text: Any = None,
        prefix_icon: Any = None,
        suffix: Any = None,
        expand: Any = None,
        dense: bool = False,
        content_padding: Any = None,
        autofocus: bool = False,
        border_radius: Any = None,
        bgcolor: Any = None,
        disabled: bool = False,
        text_size: Any = None,
    ): ...

class Dropdown(Control):
    options: list[dropdown.Option]
    value: Any
    def __init__(
        self,
        label: Any = None,
        value: Any = None,
        options: Any = None,
        on_change: Any = None,
        width: Any = None,
        height: Any = None,
        border: Any = None,
        filled: bool = False,
        expand: Any = None,
        dense: bool = False,
        content_padding: Any = None,
        hint_text: Any = None,
        border_radius: Any = None,
        bgcolor: Any = None,
        visible: bool = True,
    ): ...

class ElevatedButton(Control):
    def __init__(
        self,
        text: str = "",
        icon: Any = None,
        on_click: Any = None,
        style: Any = None,
        disabled: bool = False,
        content: Any = None,
        width: Any = None,
        height: Any = None,
        expand: Any = None,
    ): ...

class ButtonStyle:
    def __init__(
        self,
        color: Any = None,
        bgcolor: Any = None,
        padding: Any = None,
        shape: Any = None,
        elevation: Any = None,
    ): ...

class RoundedRectangleBorder:
    def __init__(self, radius: Any = None): ...

class CircleBorder:
    def __init__(self): ...

class Checkbox(Control):
    value: bool
    def __init__(
        self,
        label: Any = None,
        value: bool = False,
        on_change: Any = None,
        fill_color: Any = None,
    ): ...

class dropdown:
    class Option:
        key: Any
        text: str
        def __init__(self, key: Any, text: Any = None): ...

class ImageFit:
    COVER: Any
    CONTAIN: Any

class TextTheme:
    def __init__(self, body_medium: Any = None, title_medium: Any = None): ...

class TextStyle:
    def __init__(self, color: Any = None, size: Any = None, weight: Any = None): ...

class ScrollbarTheme:
    def __init__(
        self,
        thumb_color: Any = None,
        track_color: Any = None,
        radius: Any = None,
        thickness: Any = None,
        interactive: bool = True,
    ): ...

class InputDecorationTheme:
    def __init__(
        self,
        border: Any = None,
        focused_border: Any = None,
        label_style: Any = None,
        hint_style: Any = None,
    ): ...

class OutlineInputBorder:
    def __init__(self, border_side: Any = None, border_radius: Any = None): ...

class Tabs(Control):
    def __init__(
        self,
        tabs: Any = None,
        selected_index: int = 0,
        on_change: Any = None,
        expand: Any = None,
    ): ...

class Tab(Control):
    def __init__(
        self,
        text: str = "",
        icon: Any = None,
        content: Any = None,
    ): ...

class ListView(Control):
    controls: list[Control]
    def __init__(
        self,
        expand: Any = None,
        spacing: Any = None,
        padding: Any = None,
        auto_scroll: bool = False,
        controls: Any = None,
    ): ...
    def scroll_to(
        self,
        offset: float = 0.0,
        delta: float = 0.0,
        key: str = "",
        duration: int = 0,
        curve: Any = None,
    ) -> None: ...

class FloatingActionButton(Control):
    def __init__(
        self,
        icon: Any = None,
        on_click: Any = None,
        bgcolor: Any = None,
        content: Any = None,
    ): ...

class AlertDialog(Control):
    def __init__(
        self,
        title: Any = None,
        content: Any = None,
        actions: Any = None,
        actions_alignment: Any = None,
        modal: bool = False,
        on_dismiss: Any = None,
    ): ...

class TextButton(Control):
    def __init__(
        self,
        text: str = "",
        on_click: Any = None,
        icon: Any = None,
    ): ...

class Stack(Control):
    def __init__(
        self,
        controls: Any = None,
        expand: Any = None,
    ): ...

class ProgressRing(Control):
    def __init__(
        self,
        width: Any = None,
        height: Any = None,
        stroke_width: Any = None,
        color: Any = None,
    ): ...

class InputBorder:
    NONE: Any
    OUTLINE: Any

class TextThemeStyle:
    HEADLINE_MEDIUM: Any
    BODY_MEDIUM: Any

class ScrollMode:
    AUTO: Any

class BoxShadow:
    def __init__(
        self,
        spread_radius: Any = None,
        blur_radius: Any = None,
        color: Any = None,
        offset: Any = None,
        blur_style: Any = None,
    ): ...

class Offset:
    def __init__(self, x: Any, y: Any): ...

class margin:
    @staticmethod
    def only(
        left: Any = None, top: Any = None, right: Any = None, bottom: Any = None
    ) -> Any: ...
    @staticmethod
    def all(value: Any) -> Any: ...

class RadioGroup(Control):
    value: Any
    def __init__(
        self, content: Any = None, on_change: Any = None, value: Any = None
    ): ...

class Radio(Control):
    def __init__(
        self, value: Any = None, label: Any = None, fill_color: Any = None
    ): ...

class KeyboardEvent:
    key: str
    shift: bool
    ctrl: bool
    alt: bool
    meta: bool
    test: bool

# Relaxed types
colors: Any
icons: Any
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
        scrollbar_theme: Any = None,
        text_theme: Any = None,
        input_decoration_theme: Any = None,
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
        inverse_surface: Any = None,
        on_inverse_surface: Any = None,
        surface_variant: Any = None,
    ): ...

class VisualDensity:
    COMFORTABLE: Any

class ThemeVisualDensity:
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

class PagePlatform:
    ANDROID: Any
    IOS: Any
    MACOS: Any
    LINUX: Any
    WINDOWS: Any
