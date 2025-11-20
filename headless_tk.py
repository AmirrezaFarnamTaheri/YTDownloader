"""Headless Tkinter stand-ins used when a real display is not available."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


class _Variable:
    def __init__(self, value: Any = None):
        self._value = value

    def get(self) -> Any:
        return self._value

    def set(self, value: Any) -> None:
        self._value = value


class BooleanVar(_Variable):
    """Simple BooleanVar replacement."""
    pass


class StringVar(_Variable):
    """Simple StringVar replacement."""

    def __init__(self, value: str | None = ""):
        super().__init__(value or "")


class _BaseWidget:
    """Base widget capturing configuration state."""

    def __init__(self, master: Optional["HeadlessTk"] = None, **kwargs: Any):
        self.master = master
        self._options: Dict[str, Any] = {}
        self._bindings: Dict[str, Callable[..., Any]] = {}
        self._children: List["_BaseWidget"] = []
        if master is not None and hasattr(master, "_children"):
            master._children.append(self)
        self.config(**kwargs)

    def config(self, **kwargs: Any) -> None:
        self._options.update(kwargs)

    configure = config

    def cget(self, option: str) -> Any:
        return self._options.get(option)

    def grid(self, **kwargs: Any) -> None:  # pragma: no cover - layout is a no-op in tests
        self._options.update({f"grid_{k}": v for k, v in kwargs.items()})

    def grid_remove(self) -> None:  # pragma: no cover - layout is a no-op in tests
        self._options["grid_removed"] = True

    def grid_columnconfigure(self, column: int, weight: int) -> None:
        self._options.setdefault("grid_columnconfigure", {})[column] = weight

    def grid_rowconfigure(self, row: int, weight: int) -> None:
        self._options.setdefault("grid_rowconfigure", {})[row] = weight

    def pack(self, **kwargs: Any) -> None:  # pragma: no cover - layout is a no-op in tests
        self._options.update({f"pack_{k}": v for k, v in kwargs.items()})

    def pack_forget(self) -> None: # pragma: no cover
        pass

    def bind(self, sequence: str, func: Callable[..., Any]) -> None:
        self._bindings[sequence] = func

    def destroy(self) -> None:  # pragma: no cover - not used in tests
        pass

    def winfo_x(self) -> int: return 0
    def winfo_y(self) -> int: return 0
    def winfo_width(self) -> int: return 100
    def winfo_height(self) -> int: return 100

class Toplevel(_BaseWidget):
    """Headless Toplevel window."""
    def wm_overrideredirect(self, boolean: bool = False) -> None: pass
    def wm_geometry(self, geometry: str) -> None: pass
    def after(self, delay: int, func: Callable[..., Any]) -> None: pass


class PanedWindow(_BaseWidget):
    """Headless PanedWindow."""
    def add(self, child: Any, weight: int = 0) -> None: pass


class Scrollbar(_BaseWidget):
    """Headless Scrollbar."""
    def set(self, first: float, last: float) -> None: pass


class Listbox(_BaseWidget):
    """Headless Listbox."""

    def __init__(self, master: Optional["HeadlessTk"] = None, **kwargs: Any):
        super().__init__(master, **kwargs)
        self._items: List[str] = []

    def insert(self, index: int | str, *elements: str) -> None:
        if index == "end":
            self._items.extend(elements)
        else:
            # Simplified insert
            self._items.extend(elements)

    def delete(self, first: int | str, last: Optional[int | str] = None) -> None:
        if first == 0 and last == "end":
            self._items.clear()

    def curselection(self) -> Tuple[int, ...]:
        return (0,) if self._items else ()

    def get(self, first: int | str, last: Optional[int | str] = None) -> Any:
        if isinstance(first, int) and 0 <= first < len(self._items):
             return self._items[first]
        return ""


class Label(_BaseWidget):
    """Headless label."""


class LabelFrame(_BaseWidget):
    """Headless labelled frame."""


class Checkbutton(_BaseWidget):
    """Headless checkbutton that stores an associated variable."""

    def __init__(self, master: Optional["HeadlessTk"] = None, variable: Optional[_Variable] = None, **kwargs: Any):
        super().__init__(master, **kwargs)
        self.variable = variable or BooleanVar()


class Entry(_BaseWidget):
    """Headless entry widget supporting minimal text operations."""

    def __init__(self, master: Optional["HeadlessTk"] = None, **kwargs: Any):
        super().__init__(master, **kwargs)
        self._text = ""

    def get(self) -> str:
        return self._text

    def insert(self, index: int | str, text: str) -> None:
        if index in (0, "0"):
            self._text = text + self._text
        else:
            self._text += text

    def delete(self, start: int | str, end: Optional[int | str] = None) -> None:
        if start in (0, "0") and (end in (None, "end") or isinstance(end, str) and end.lower() == "end"):
            self._text = ""
        elif start in (0, "0") and isinstance(end, int):
            self._text = self._text[end:]
        else:
            self._text = ""


class Button(_BaseWidget):
    """Headless button storing a callable command."""

    def __init__(self, master: Optional["HeadlessTk"] = None, command: Optional[Callable[[], Any]] = None, **kwargs: Any):
        super().__init__(master, **kwargs)
        self._command = command

    def invoke(self) -> None:  # pragma: no cover - not used in tests
        if self._command:
            self._command()


class Progressbar(_BaseWidget):
    """Headless progress bar tracking a numeric value."""

    def __init__(self, master: Optional["HeadlessTk"] = None, **kwargs: Any):
        super().__init__(master, **kwargs)
        self._value = 0

    def __setitem__(self, key: str, value: Any) -> None:
        self._options[key] = value
        if key == "value":
            self._value = value

    def __getitem__(self, key: str) -> Any:
        if key == "value":
            return self._value
        return self._options.get(key)


class Menu:
    """Headless menu keeping a list of commands."""

    def __init__(self, master: Optional["HeadlessTk"] = None, tearoff: int = 1):
        self.master = master
        self.tearoff = tearoff
        self._commands: List[Tuple[str, Callable[..., Any]]] = []

    def add_command(self, label: str, command: Callable[..., Any]) -> None:
        self._commands.append((label, command))

    def add_cascade(self, label: str, menu: "Menu") -> None:  # pragma: no cover - no-op
        self._commands.append((label, menu))

    def post(self, _x: int, _y: int) -> None:  # pragma: no cover - no GUI in tests
        pass


class Notebook(_BaseWidget):
    """Headless notebook storing tab information."""

    def __init__(self, master: Optional["HeadlessTk"] = None, **kwargs: Any):
        super().__init__(master, **kwargs)
        self._tabs: List[Tuple[_BaseWidget, str]] = []

    def add(self, child: _BaseWidget, text: str) -> None:
        self._tabs.append((child, text))

    def tab(self, index: int, option: str) -> Any:
        if option == "text":
            return self._tabs[index][1]
        raise KeyError(option)

    def index(self, what: str) -> int:
        if what == "end":
            return len(self._tabs)
        raise KeyError(what)


class Treeview(_BaseWidget):
    """Headless treeview managing tabular data."""

    def __init__(self, master: Optional["HeadlessTk"] = None, columns: Sequence[str] = (), show: str = "tree", selectmode: str = "browse"):
        super().__init__(master)
        self.columns = columns
        self.show = show
        self._items: Dict[str, Dict[str, Any]] = {}
        self._order: List[str] = []
        self._selection: List[str] = []
        self._headings: Dict[str, Dict[str, Any]] = {}
        self._columns: Dict[str, Dict[str, Any]] = {}

    def heading(self, column: str, **kwargs: Any) -> None:
        self._headings[column] = kwargs

    def column(self, column: str, **kwargs: Any) -> None:
        self._columns[column] = kwargs

    def yview(self, *args): pass

    def insert(self, _parent: str, _index: str, iid: Optional[int | str] = None, values: Sequence[Any] = ()) -> None:
        iid_str = str(iid) if iid is not None else str(len(self._items))
        if iid_str not in self._items:
            self._order.append(iid_str)
        self._items[iid_str] = {"values": tuple(values)}

    def delete(self, iid: str) -> None:
        iid_str = str(iid)
        if iid_str in self._items:
            del self._items[iid_str]
        if iid_str in self._order:
            self._order.remove(iid_str)
        if iid_str in self._selection:
            self._selection.remove(iid_str)

    def get_children(self) -> Tuple[str, ...]:
        return tuple(self._order)

    def selection_set(self, items: Sequence[int | str]) -> None:
        if isinstance(items, (list, tuple, set)):
            self._selection = [str(i) for i in items]
        else:
            self._selection = [str(items)]

    def selection(self) -> Tuple[str, ...]:
        return tuple(self._selection)

    def identify_row(self, _y: int) -> Optional[str]:  # pragma: no cover - not used in tests
        return self._order[0] if self._order else None

    def item(self, item: str, option: Optional[str] = None, **kwargs: Any) -> Any:
        if item in self._items:
             if option is None and not kwargs:
                 return self._items[item]
             # Support setting/getting specific options if needed
        return {}


class Combobox(_BaseWidget):
    """Headless combobox managing a simple list of values."""

    def __init__(self, master: Optional["HeadlessTk"] = None, textvariable: Optional[_Variable] = None, values: Sequence[str] = (), **kwargs: Any):
        super().__init__(master, **kwargs)
        self.variable = textvariable or StringVar()
        self._values: Tuple[str, ...] = tuple(values)

    def set(self, value: str) -> None:
        self.variable.set(value)

    def get(self) -> str:
        return str(self.variable.get())

    def __getitem__(self, key: str) -> Any:
        if key == "values":
            return self._values
        return self._options.get(key)

    def config(self, **kwargs: Any) -> None:
        super().config(**kwargs)
        if "values" in kwargs:
            self._values = tuple(kwargs["values"])


class Style:
    """Headless ttk style placeholder."""

    def configure(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - no-op
        pass

    def map(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - no-op
        pass


class HeadlessTk:
    """Replacement for tk.Tk that stores configuration without opening windows."""

    def __init__(self, *_, **__):
        self._children: List[_BaseWidget] = []
        self._after_calls: List[Tuple[int, Callable[..., Any]]] = []
        self._options: Dict[str, Any] = {}
        self.tk = self # Mock tk attribute

    def title(self, title: str) -> None:
        self._options["title"] = title

    def geometry(self, geometry: str = "") -> Optional[str]:
        if geometry:
            self._options["geometry"] = geometry
            return None
        return self._options.get("geometry", "")

    def minsize(self, width: int, height: int) -> None:
        self._options["minsize"] = (width, height)

    def config(self, **kwargs: Any) -> None:
        self._options.update(kwargs)

    def update_idletasks(self) -> None: pass

    def bind(self, sequence: str, func: Callable[..., Any]) -> None: pass

    def iconbitmap(self, bitmap: str) -> None: pass

    def clipboard_get(self) -> str: return ""

    def attributes(self, *args) -> Any: pass

    configure = config

    def grid_columnconfigure(self, column: int, weight: int) -> None:
        self._options.setdefault("grid_columnconfigure", {})[column] = weight

    def grid_rowconfigure(self, row: int, weight: int) -> None:
        self._options.setdefault("grid_rowconfigure", {})[row] = weight

    def after(self, delay: int, func: Callable[..., Any]) -> str:
        self._after_calls.append((delay, func))
        return "after_id"

    def after_cancel(self, id: str) -> None:
        pass

    def winfo_x(self) -> int: return 0
    def winfo_y(self) -> int: return 0
    def winfo_width(self) -> int: return 800
    def winfo_height(self) -> int: return 600

    def withdraw(self) -> None:
        pass

    def destroy(self) -> None:  # pragma: no cover - not used in tests
        self._children.clear()


class _DummyFileDialog:
    def askdirectory(self) -> Optional[str]:
        return None

    def askopenfilename(self, **kwargs) -> Optional[str]:
        return None


class _DummyMessagebox:
    def showwarning(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def showerror(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def showinfo(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def askyesno(self, *_args: Any, **_kwargs: Any) -> bool:
        return False


def patch_tkinter():
    """Patch the tkinter module with headless stand-ins.

    Returns
    -------
    tuple
        Patched tkinter module, ttk stand-ins, filedialog stub, messagebox stub.
    """

    import tkinter as tk_module

    tk_module.Tk = HeadlessTk  # type: ignore[assignment]
    tk_module.Toplevel = Toplevel # type: ignore[assignment]
    tk_module.BooleanVar = BooleanVar  # type: ignore[assignment]
    tk_module.StringVar = StringVar  # type: ignore[assignment]
    tk_module.Menu = Menu  # type: ignore[assignment]
    tk_module.Listbox = Listbox # type: ignore[assignment]
    tk_module.END = "end"  # type: ignore[attr-defined]
    tk_module._ytdownloader_headless = True  # type: ignore[attr-defined]

    ttk_module = type(
        "ttk",
        (),
        {
            "Frame": _BaseWidget,
            "Label": Label,
            "LabelFrame": LabelFrame,
            "Entry": Entry,
            "Button": Button,
            "Checkbutton": Checkbutton,
            "Combobox": Combobox,
            "Treeview": Treeview,
            "Progressbar": Progressbar,
            "Notebook": Notebook,
            "PanedWindow": PanedWindow,
            "Scrollbar": Scrollbar,
            "Style": Style,
        },
    )()

    filedialog = _DummyFileDialog()
    messagebox = _DummyMessagebox()

    return tk_module, ttk_module, filedialog, messagebox


__all__ = [
    "patch_tkinter",
    "HeadlessTk",
    "BooleanVar",
    "StringVar",
]
