"""Renderer for BUI: Blender's user interface as a standalone library.

See https://github.com/ppmpreetham/BUI (``pip install blenderui``).

Elements are the components of ``blenderui.components`` (each of them is a
node of BUI's C kit). Template tags map to the component classes by name,
case-insensitive and with dashes and underscores removed, so ``<number-slider>``,
``<numberslider>`` and ``<NumberSlider>`` all create a ``NumberSlider``.

Top-level elements (elements inserted into a target that is not a BUI node,
for instance ``None``) are shown in their own window. Use the ``<window>``
element to control the title and size of the window; any other top-level
element is wrapped in a default window.
"""

from __future__ import annotations

import inspect
import logging
import queue
import warnings
from functools import lru_cache
from typing import Any, Callable

import blenderui  # noqa: F401 (registers the ``blenderui.*`` aliases)
import buipy
from blenderui import components as bc
from observ import scheduler

from collagraph.constants import EventLoopType

from . import Renderer

logger = logging.getLogger(__name__)

# Interval (ms) at which callbacks scheduled from other threads are run
# (only while hot reloading, see BuiRenderer.get_threadsafe_scheduler)
THREADSAFE_POLL_INTERVAL = 100


def normalize_name(name: str) -> str:
    """Normalize element and attribute names: ``number-slider`` -> ``numberslider``."""
    return name.lower().replace("-", "").replace("_", "")


def _snake_case(name: str) -> str:
    """Convert kebab-case names to snake_case: ``text-align`` -> ``text_align``."""
    return name.replace("-", "_")


class TextElement:
    """Text element (e.g. the text in ``<label>Count: {{ count }}</label>``).

    Text elements are not nodes in the kit tree. Instead, the parent keeps an
    ordered list of its text elements and the joined content of those is set
    as the text of the parent (the ``text`` property for labels and buttons,
    or the ``label`` property for value components such as checkboxes).
    """

    __slots__ = ("content", "parent")

    def __init__(self):
        self.content = ""
        self.parent = None

    def __repr__(self):
        return f"<TextElement {self.content!r}>"


class Window(bc.Column):
    """Top-level window that hosts a tree of components.

    The window's ``ctx`` (a ``buipy.KitContext``) is created when the window is
    inserted into the render target. The ``host`` window (``bui.host.Window``)
    is created at the same time, unless the renderer is headless.
    """

    def __init__(self):
        u = buipy.kit_unit()
        super().__init__(padding=round(0.4 * u), spacing=round(0.3 * u))
        self._title = "Collagraph"
        self._size = (420, 640)
        self.ctx = None
        self.host = None
        self.on_close = None

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = str(value)
        if self.host is not None:
            self.host.title(self._title)

    @property
    def size(self) -> tuple[int, int]:
        if self.host is not None:
            return tuple(self.host.size)
        return self._size

    @size.setter
    def size(self, value) -> None:
        w, h = value
        self._size = (int(w), int(h))
        if self.host is not None:
            self.host.set_size(*self._size)

    def open(self, show: bool = True) -> None:
        """Create the kit context and (if ``show``) the host window."""
        if self.ctx is None:
            self.ctx = buipy.KitContext(self)
        if show and self.host is None:
            from blenderui import host

            self.host = host.Window(self.ctx, self._title, self._size)
            self.host.on_close = self._close_requested
            self.host.show()

    def close(self) -> None:
        """Close the host window."""
        if self.host is not None:
            host_window, self.host = self.host, None
            host_window.close()

    def render(self, width: int | None = None, height: int | None = None):
        """Render the window headlessly into a ``buipy.Raster`` and return it.

        Useful for tests and screenshots. Layout is updated as part of the
        render, so call this before reading geometry (``rect``) of elements.
        """
        if self.ctx is None:
            self.open(show=False)
        w, h = width or self._size[0], height or self._size[1]
        raster = getattr(self, "_raster", None)
        if raster is None or raster.size != (w, h):
            raster = self._raster = buipy.Raster(w, h)
        self.ctx.render(w, h, raster, True)
        return raster

    def _close_requested(self) -> bool:
        if self.on_close is not None:
            result = self.on_close()
            # Only an explicit False keeps the window open
            return result is not False
        return True


def _split():
    # Split requires a left and right element on construction, but in a
    # template, the children are inserted later. Their ``weight`` attributes
    # determine how the width is divided.
    el = bc.Split.__new__(bc.Split)
    bc.Row.__init__(el)
    return el


def _scroll_view():
    # ScrollView requires its child on construction, which is inserted later.
    el = bc.ScrollView.__new__(bc.ScrollView)
    bc.Component.__init__(el)
    el.set("rows", 8)
    return el


# Mapping from (normalized) element name to a callable that creates the element
TYPE_MAPPING: dict[str, Callable[[], buipy.KitNode]] = {}

# Components that need arguments for construction
FACTORIES: dict[type, Callable[[], buipy.KitNode]] = {
    bc.Panel: lambda: bc.Panel(""),
    bc.Tabs: lambda: bc.Tabs([]),
    bc.SideTabs: lambda: bc.SideTabs([]),
    bc.IconButton: lambda: bc.IconButton(""),
    bc.MenuButton: lambda: bc.MenuButton("", []),
    bc.Popover: lambda: bc.Popover(""),
    bc.ScrollView: _scroll_view,
    bc.Split: _split,
}

# Base classes in blenderui.components that should not be elements
_EXCLUDED = {bc.Component, bc.ValueComponent}

for _name in bc.__all__:
    _cls = getattr(bc, _name)
    if (
        isinstance(_cls, type)
        and issubclass(_cls, buipy.KitNode)
        and _cls not in _EXCLUDED
    ):
        TYPE_MAPPING[normalize_name(_name)] = FACTORIES.get(_cls, _cls)

TYPE_MAPPING.update(
    {
        "window": Window,
        # Shorter aliases, mostly following the kit's node type names
        "enum": bc.EnumRow,
        "number": bc.NumberField,
        "progress": bc.ProgressBar,
        "scroll": _scroll_view,
        "slider": bc.NumberSlider,
        "swatch": bc.ColorSwatch,
    }
)

# Aliases for event names, to make the names of PySide's signals work as well
EVENT_ALIASES = {
    "clicked": "click",
    "changed": "change",
    "toggled": "toggle",
}

# Attributes that are used by collagraph itself (e.g. for keyed v-for)
IGNORED_ATTRIBUTES = {"key"}

# Default values of (Python) properties, per (type, attribute)
DEFAULT_VALUES: dict[tuple[type, str], Any] = {}

_MISSING = object()


def _property(el: Any, attr: str) -> property | None:
    """Returns the (settable) Python property ``attr`` of the type of ``el``."""
    prop = getattr(type(el), attr, None)
    if isinstance(prop, property) and prop.fset is not None:
        return prop
    return None


def _text_property(el: Any) -> str:
    """Returns the name of the property that holds the text of ``el``."""
    for attr in ("text", "label"):
        if _property(el, attr):
            return attr
    raise TypeError(f"Element '{el.type}' does not support text content")


@lru_cache(maxsize=None)
def _set_value_supports_notify(typ: type) -> bool:
    return "notify" in inspect.signature(typ.set_value).parameters


def _supports_notify(el: Any) -> bool:
    """Whether the ``set_value`` method of ``el`` has a ``notify`` argument."""
    return _set_value_supports_notify(type(el))


def _zero_value(value: Any) -> Any:
    """Value that 'resets' a kit property that was set to ``value``."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return 0
    if isinstance(value, str):
        return ""
    if isinstance(value, (list, tuple)):
        return type(value)()
    return None


class BuiRenderer(Renderer):
    """Renderer for BUI (Blender's UI as a library: ``pip install blenderui``).

    Render into any target that is not a BUI node (for instance ``None``):
    every top-level element is shown in its own window. Call :meth:`run` to
    run BUI's event loop until all windows are closed::

        renderer = cg.BuiRenderer()
        gui = cg.Collagraph(renderer=renderer)
        gui.render(MyComponent, None)
        renderer.run()

    With ``headless=True``, no windows are opened. The top-level ``Window``
    elements (see :attr:`windows`) can then be rendered and driven
    programmatically, which is useful for tests.
    """

    def __init__(self, headless: bool = False):
        super().__init__()
        self.headless = headless
        self.windows: list[Window] = []
        # Callbacks scheduled from other threads (see get_threadsafe_scheduler)
        self._threadsafe_calls: queue.SimpleQueue | None = None
        self._polling = False

    def preferred_event_loop_type(self):
        return EventLoopType.DEFAULT

    def register_asyncio(self):
        # BUI runs its own event loop (native or Tk), not asyncio. So instead
        # of relying on asyncio, flushes are scheduled on BUI's event loop.
        scheduler.register_request_flush(self.request_flush)

    def request_flush(self):
        """Schedule a flush of the observ scheduler on BUI's event loop.

        When no window is open (yet), the flush happens immediately.
        """
        for window in self.windows:
            if window.host is not None and window.host.is_open:
                window.host.after(0, scheduler.flush)
                return
        scheduler.flush()

    def get_threadsafe_scheduler(self):
        """Returns a function that schedules a callback on BUI's event loop.

        The returned function can be called from any thread. BUI's timers
        can only be used from the main thread, so the callbacks are put in a
        queue that is polled on the main thread while windows are open.
        Polling only starts once this method is called (by the hot reloader).

        Returns None for headless renderers: there is no event loop to run
        the callbacks on.
        """
        if self.headless:
            return None
        if self._threadsafe_calls is None:
            self._threadsafe_calls = queue.SimpleQueue()
        self._start_polling()
        return self._threadsafe_calls.put

    def _start_polling(self):
        if self._polling or self._threadsafe_calls is None:
            return
        self._polling = self._schedule_poll()

    def _schedule_poll(self) -> bool:
        for window in self.windows:
            if window.host is not None and window.host.is_open:
                window.host.after(THREADSAFE_POLL_INTERVAL, self._poll)
                return True
        return False

    def _poll(self):
        while True:
            try:
                callback = self._threadsafe_calls.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception:
                logger.exception("Error in callback %r", callback)
        # The callback (e.g. a hot reload) might have replaced the windows,
        # so look for an open window again. Polling stops when all windows
        # are closed and starts again when a new window opens.
        self._polling = self._schedule_poll()

    def run(self):
        """Run BUI's event loop until all windows are closed."""
        from blenderui import host

        host.run()

    @classmethod
    def register_element(cls, type_name: str, typ: Callable | None = None):
        """Register a type (or factory) that can be created as an element.

        Can be used as a decorator as well::

            @BuiRenderer.register_element("my-widget")
            class MyWidget(bc.Row): ...
        """
        if typ is None:

            def wrapper(typ):
                cls.register_element(type_name, typ=typ)
                return typ

            return wrapper

        type_name = normalize_name(type_name)
        if type_name in TYPE_MAPPING:
            warnings.warn(f"{type_name} element already registered")
        if isinstance(typ, type) and not issubclass(typ, buipy.KitNode):
            raise TypeError(f"Specified type '{typ}' not a subclass of KitNode")
        TYPE_MAPPING[type_name] = typ

    def create_element(self, type: str) -> buipy.KitNode:
        factory = TYPE_MAPPING.get(normalize_name(type))
        if factory is None:
            raise ValueError(f"Can't create element of type: {type}")
        return factory()

    def create_text_element(self) -> TextElement:
        return TextElement()

    def _container(self, parent: buipy.KitNode) -> buipy.KitNode:
        """Returns the node that holds the children of ``parent``."""
        if isinstance(parent, bc.Panel):
            return parent.body
        return parent

    def insert(self, el: Any, parent: Any, anchor: Any = None):
        if isinstance(el, TextElement):
            self._insert_text(el, parent, anchor)
            return

        if not isinstance(parent, buipy.KitNode):
            self._insert_window(el)
            return

        container = self._container(parent)
        if el.parent is container:
            # Moving an element within its parent: remove it first so
            # that the index of the anchor is correct.
            buipy.KitNode.remove(container, el)

        index = -1
        if anchor is not None and not isinstance(anchor, TextElement):
            for idx, child in enumerate(container.children):
                if child is anchor:
                    index = idx
                    break
            else:
                warnings.warn(f"Could not find anchor {anchor} in {parent}")
        buipy.KitNode.add(container, el, index)

    def _insert_window(self, el: buipy.KitNode):
        if isinstance(el, Window):
            window = el
        else:
            # Wrap any other top-level element in a window
            window = Window()
            buipy.KitNode.add(window, el)
            el._cg_window = window
        window.open(show=not self.headless)
        self.windows.append(window)
        self._start_polling()

    def _insert_text(self, el: TextElement, parent: Any, anchor: Any = None):
        if not isinstance(parent, buipy.KitNode):
            raise TypeError("Text elements can't be rendered at the top-level")
        # Check early that the parent supports text
        _text_property(parent)
        proxies = parent.__dict__.setdefault("_cg_text_elements", [])
        if el in proxies:
            proxies.remove(el)
        index = len(proxies)
        if isinstance(anchor, TextElement) and anchor in proxies:
            index = proxies.index(anchor)
        proxies.insert(index, el)
        el.parent = parent
        self._sync_text(parent)

    def _sync_text(self, parent: buipy.KitNode):
        proxies = parent.__dict__.get("_cg_text_elements", [])
        setattr(
            parent,
            _text_property(parent),
            "".join(proxy.content for proxy in proxies),
        )

    def remove(self, el: Any, parent: Any):
        if isinstance(el, TextElement):
            proxies = parent.__dict__.get("_cg_text_elements", [])
            if el in proxies:
                proxies.remove(el)
            el.parent = None
            self._sync_text(parent)
            return

        if not isinstance(parent, buipy.KitNode):
            window = el if isinstance(el, Window) else el.__dict__.get("_cg_window")
            if window is not None:
                window.close()
                if window in self.windows:
                    self.windows.remove(window)
            return

        buipy.KitNode.remove(self._container(parent), el)

    def set_element_text(self, el: TextElement, value: str):
        el.content = "" if value is None else str(value)
        if el.parent is not None:
            self._sync_text(el.parent)

    def set_attribute(self, el: Any, attr: str, value: Any):
        attr = _snake_case(attr)
        if attr in IGNORED_ATTRIBUTES:
            return

        if attr == "value" and hasattr(el, "set_value"):
            # Setting the value from code should not trigger change events
            if _supports_notify(el):
                el.set_value(value, notify=False)
            else:
                el.set_value(value)
            return

        if _property(el, attr):
            key = (type(el), attr)
            if key not in DEFAULT_VALUES:
                DEFAULT_VALUES[key] = getattr(el, attr, None)
            setattr(el, attr, value)
            return

        # Not a Python property, so set it as a property of the kit node.
        # Remember the value so that the attribute can be reset on removal.
        el.__dict__.setdefault("_cg_kit_attrs", {})[attr] = value
        el.set(attr, value)

    def remove_attribute(self, el: Any, attr: str, value: Any):
        attr = _snake_case(attr)
        if attr in IGNORED_ATTRIBUTES:
            return

        if attr == "value" and hasattr(el, "reset"):
            el.reset()
            return

        if _property(el, attr):
            default = DEFAULT_VALUES.get((type(el), attr), _MISSING)
            if default is not _MISSING:
                setattr(el, attr, default)
            return

        kit_attrs = el.__dict__.get("_cg_kit_attrs", {})
        if attr in kit_attrs:
            el.set(attr, _zero_value(kit_attrs.pop(attr)))

    def _event_attr(self, el: Any, event_type: str) -> str:
        name = _snake_case(event_type)
        name = EVENT_ALIASES.get(name, name)
        attr = f"on_{name}"
        if not hasattr(el, attr):
            raise ValueError(
                f"Element '{el.type}' ({type(el).__name__}) "
                f"does not support the '{event_type}' event"
            )
        return attr

    def add_event_listener(self, el: Any, event_type: str, value: Callable):
        attr = self._event_attr(el, event_type)
        listeners = el.__dict__.setdefault("_cg_listeners", {})
        if attr not in listeners:
            handlers = listeners[attr] = []
            original = getattr(el, attr)

            def dispatch(*args):
                result = None
                if original is not None:
                    result = original(*args)
                for handler in list(handlers):
                    handler_result = handler(*args)
                    if handler_result is not None:
                        result = handler_result
                return result

            setattr(el, attr, dispatch)
        listeners[attr].append(value)

    def remove_event_listener(self, el: Any, event_type: str, value: Callable):
        attr = self._event_attr(el, event_type)
        handlers = el.__dict__.get("_cg_listeners", {}).get(attr)
        if handlers and value in handlers:
            handlers.remove(value)

    def save_element_state(self, el: Any) -> dict | None:
        window = el if isinstance(el, Window) else el.__dict__.get("_cg_window")
        if window is None or window.host is None:
            return None
        state = {"size": window.size}
        if pos := window.host.wm_get("pos"):
            state["pos"] = pos
        return state

    def restore_element_state(self, el: Any, state: dict) -> None:
        window = el if isinstance(el, Window) else el.__dict__.get("_cg_window")
        if window is None or window.host is None:
            return
        if size := state.get("size"):
            window.size = size
        if pos := state.get("pos"):
            window.host.wm("pos", *pos)
