"""
Renderer for GPUI (the GPU-accelerated UI framework from the Zed editor),
through the `gpyui <https://github.com/gtrefalt/gpyui>`_ Python bindings.

gpyui exposes a retained tree of Python ``Control`` handles that is mirrored
into native GPUI / GPUI Kit components. This renderer maps template tags onto
those controls.

Elements are created lazily: ``create_element`` returns a :class:`GpuiElement`
handle that collects the static attributes, bindings and event listeners of an
element. The actual gpyui control is constructed when the element is first
inserted into the tree, with all collected properties as keyword arguments.
That way gpyui validates related properties together (for instance the
``items`` and ``value`` of a ``<radio-group>``) and construction-only
properties (such as the range of a ``<slider>``) can be set from templates.
"""

from __future__ import annotations

import asyncio
import copy
import inspect
from collections.abc import Callable, Mapping
from typing import Any, ClassVar

import gpyui
from gpyui.controls import Column, Control
from gpyui.widgets import KitControl
from observ import to_raw

from collagraph.constants import EventLoopType

from . import Renderer

__all__ = ["GpuiElement", "GpuiRenderer", "GpuiTextElement", "GpuiWindow"]


# Style properties that gpyui supports through `Control.style()`, mapped
# onto the type that static (string) template attributes are coerced to
STYLE_PROPERTIES: dict[str, type] = {
    **dict.fromkeys(
        (
            "width",
            "height",
            "min_width",
            "min_height",
            "padding",
            "gap",
            "radius",
            "font_size",
            "flex",
        ),
        float,
    ),
    **dict.fromkeys(("full_width", "full_height", "border", "bold"), bool),
    **dict.fromkeys(("background", "color", "align", "justify"), str),
}

# Short names for some of the controls, next to the (normalized) class names
ALIASES: dict[str, str] = {
    "input": "textinput",
    "lineedit": "textinput",
    "text": "label",
    "vbox": "column",
    "hbox": "row",
    "scrollarea": "scroll",
    "progressbar": "progress",
    "spinbox": "numberinput",
    "tooltipcontainer": "tooltip",
}

# Keyword arguments that are required to construct some controls
REQUIRED_ARGUMENTS: dict[type, dict[str, Any]] = {
    gpyui.Button: {"text": ""},
    gpyui.DropdownMenu: {"text": "", "items": ()},
}


def normalize_name(name: str) -> str:
    """Normalize a tag name: case insensitive and without dashes/underscores."""
    return name.replace("-", "").replace("_", "").lower()


def normalize_attribute(name: str) -> str:
    return name.replace("-", "_")


class GpuiTextElement:
    """
    Text element (text content in templates).

    Inside containers (e.g. ``<column>``) text elements are shown with a
    ``Label`` control. Inside controls that have a ``text`` property
    (e.g. ``<button>``, ``<label>``, ``<markdown>``), the joined content of all
    text elements is set as the text of that control.
    """

    def __init__(self):
        self.content = ""
        self.control: Control | None = None
        # The element this text is the text of (when not shown as label)
        self.text_parent: GpuiElement | None = None
        self.attached = False

    def __repr__(self):
        return f"<GpuiTextElement({self.content!r})>"


class GpuiElement:
    """
    Handle for a gpyui control.

    The ``control`` attribute holds the gpyui ``Control`` once the element is
    inserted into the tree (and stays ``None`` before that). Template refs
    point to these handles, so use ``ref.control`` to call methods on the
    gpyui control itself.
    """

    def __init__(self, tag: str, factory: Callable[..., Control]):
        self.tag = tag
        self.factory = factory
        self.control: Control | None = None
        self.properties: dict[str, Any] = {}
        self.style: dict[str, Any] = {}
        self.visible = True
        self.listeners: dict[str, list[Callable]] = {}
        self.text_children: list[GpuiTextElement] = []
        self.attached = False

    @property
    def control_class(self) -> type:
        factory = self.factory
        return factory if isinstance(factory, type) else type(None)

    def __repr__(self):
        return f"<GpuiElement({self.tag!r}, control={self.control!r})>"


class GpuiWindow:
    """
    Handle for the ``<window>`` element: the ``gpyui.Application`` it is
    rendered into. Its attributes (``title``, ``theme``, ``width`` and
    ``height``) configure the application window, and its children become
    the root controls of the application.
    """

    ATTRIBUTES = ("title", "theme", "width", "height")

    def __init__(self, tag: str):
        self.tag = tag
        self.app: gpyui.Application | None = None
        self.properties: dict[str, Any] = {}

    @property
    def control(self) -> gpyui.Application | None:
        return self.app

    def apply(self) -> None:
        app = self.app
        if app is None:
            return
        props = self.properties
        if "title" in props and app.title != props["title"]:
            app.title = props["title"]
        if "theme" in props:
            app.theme = props["theme"]
        if "width" in props or "height" in props:
            width = props.get("width", app.width)
            height = props.get("height", app.height)
            if (width, height) != (app.width, app.height):
                app.resize(width, height)

    def __repr__(self):
        return f"<GpuiWindow(app={self.app!r})>"


class GpuiRenderer(Renderer):
    """
    GPUI renderer, based on gpyui.

    Render into a ``gpyui.Application`` (or any gpyui container control)::

        app = gpyui.Application(title="Counter")
        gui = cg.Collagraph(renderer=cg.GpuiRenderer())
        gui.render(Counter, app)
        app.run()
    """

    # Registry of tag name (normalized) -> factory of gpyui controls
    ELEMENTS: ClassVar[dict[str, Callable[..., Control]]] = {}

    def __init__(self):
        super().__init__()
        self._app: gpyui.Application | None = None
        self._detached: list[GpuiElement | GpuiTextElement] = []
        self._collect_scheduled = False

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    @classmethod
    def register_element(cls, name: str, factory: Callable[..., Control] | None = None):
        """
        Register a ``gpyui.Control`` subclass for a tag name. The supported
        attributes and events are derived from the class. Can be used as a
        class decorator as well::

            @GpuiRenderer.register_element("fancy-panel")
            class FancyPanel(gpyui.Container): ...
        """
        if factory is None:

            def wrapper(factory):
                cls.register_element(name, factory)
                return factory

            return wrapper
        if not (isinstance(factory, type) and issubclass(factory, Control)):
            raise TypeError(f"Expected a gpyui Control subclass, got {factory!r}")
        cls.ELEMENTS[normalize_name(name)] = factory
        return factory

    @classmethod
    def element_types(cls) -> dict[str, Callable[..., Control]]:
        """Return all known tag names (normalized) and their factories."""
        return dict(cls.ELEMENTS)

    # ------------------------------------------------------------------
    # Event loop integration
    # ------------------------------------------------------------------

    def preferred_event_loop_type(self) -> EventLoopType:
        return EventLoopType.DEFAULT

    def register_asyncio(self) -> None:
        """
        gpyui runs Python callbacks on its own asyncio loop, in a worker
        thread, which only exists while the application runs. Before that
        (when rendering before ``app.run()``) there is no loop at all.
        So instead of observ's default asyncio integration, flush:

        * on the running loop, when called from the callback loop
        * through ``app.call_soon``, when called from another thread
          while the application runs
        * synchronously, when there is no running application yet
        """
        from observ import scheduler

        def request_flush():
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            else:
                loop.call_soon(scheduler.flush)
                return
            if self.call_soon_threadsafe(scheduler.flush):
                return
            scheduler.flush()

        scheduler.register_request_flush(request_flush)

    def call_soon_threadsafe(self, callback: Callable[[], Any]) -> bool:
        """Schedule `callback` on gpyui's callback loop, from any thread."""
        if self._app is None:
            return False
        try:
            self._app.call_soon(callback)
        except gpyui.ApplicationClosedError:
            return False
        return True

    # ------------------------------------------------------------------
    # Elements
    # ------------------------------------------------------------------

    def create_element(self, type: str) -> GpuiElement | GpuiWindow:
        name = normalize_name(type)
        if name == "window":
            return GpuiWindow(type)
        name = ALIASES.get(name, name)
        try:
            factory = self.ELEMENTS[name]
        except KeyError:
            raise ValueError(
                f"Unknown gpui element type: '{type}'. Register custom types with "
                "GpuiRenderer.register_element()"
            ) from None
        return GpuiElement(type, factory)

    def create_text_element(self) -> GpuiTextElement:
        return GpuiTextElement()

    def insert(self, el: Any, parent: Any, anchor: Any = None):
        if isinstance(el, GpuiWindow):
            if not isinstance(parent, gpyui.Application):
                raise TypeError(
                    "<window> can only be rendered into a gpyui.Application, "
                    f"not {parent!r}"
                )
            el.app = self._app = parent
            el.apply()
            return
        if isinstance(parent, GpuiElement):
            native_parent = self._realize(parent)
        else:
            native_parent = self._native(parent)
        if isinstance(native_parent, gpyui.Application):
            self._app = native_parent

        if isinstance(el, GpuiTextElement) and not _is_container(native_parent):
            if not isinstance(parent, GpuiElement):
                raise TypeError(f"Can't insert text into {parent!r}")
            self._insert_text(el, parent, anchor)
            return

        control = self._realize(el)
        el.attached = True
        children = [child for child in native_parent.children if child is not control]
        index = len(children)
        if anchor is not None:
            anchor_control = self._native(anchor)
            if anchor_control in children:
                index = children.index(anchor_control)
        children.insert(index, control)
        native_parent.set_children(children)

    def remove(self, el: Any, parent: Any):
        if isinstance(el, GpuiWindow):
            # The children of the window remove themselves
            el.app = None
            return
        if isinstance(el, GpuiTextElement) and el.text_parent is not None:
            text_parent = el.text_parent
            text_parent.text_children.remove(el)
            el.text_parent = None
            el.attached = False
            self._sync_text(text_parent)
            return

        control = el.control if isinstance(el, GpuiElement | GpuiTextElement) else el
        native_parent = self._native(parent)
        if control is None or control.disposed or native_parent is None:
            return
        if control in native_parent.children:
            native_parent.remove(control)
        if isinstance(el, GpuiElement | GpuiTextElement):
            el.attached = False
            # Elements might be removed and inserted again (for instance when
            # moving items in a keyed v-for), so only release the control
            # when it is still detached at the end of the current tick
            self._detached.append(el)
            self._schedule_collect()

    def set_element_text(self, el: GpuiTextElement, value: str):
        el.content = value
        if el.text_parent is not None:
            self._sync_text(el.text_parent)
        elif el.control is not None:
            el.control.text = value

    def set_attribute(self, el: GpuiElement, attr: str, value: Any):
        name = normalize_attribute(attr)
        if name == "key":
            # Keys are used by collagraph for v-for, not by gpyui
            return
        # gpyui validates with strict type checks: unwrap reactive proxies
        # (and copy containers, so later mutations of state don't leak in)
        value = to_raw(value)
        if isinstance(value, dict | list | set | tuple):
            value = copy.deepcopy(value)
        if isinstance(el, GpuiWindow):
            if name not in GpuiWindow.ATTRIBUTES:
                raise AttributeError(
                    f"Unknown attribute '{attr}' for <{el.tag}>. "
                    f"Supported attributes: {list(GpuiWindow.ATTRIBUTES)}"
                )
            if name in ("width", "height"):
                value = _coerce(float, value)
            el.properties[name] = value
            el.apply()
            return
        cls = el.control_class
        if name == "style":
            if not isinstance(value, Mapping):
                raise TypeError(f"style requires a dict, got {value!r}")
            style = {
                key: _coerce(STYLE_PROPERTIES.get(key), val)
                for key, val in value.items()
            }
            self._set_style(el, style)
        elif name == "visible":
            el.visible = _coerce(bool, value)
            if el.control is not None:
                el.control.visible = el.visible
        elif name in _properties(cls):
            value = _coerce(_property_type(cls, name), value)
            el.properties[name] = value
            if el.control is not None:
                self._update_property(el, name, value)
        elif name in STYLE_PROPERTIES:
            value = _coerce(STYLE_PROPERTIES[name], value)
            self._set_style(el, {**el.style, name: value})
        else:
            raise AttributeError(
                f"Unknown attribute '{attr}' for <{el.tag}>. Supported attributes: "
                f"{sorted(_properties(cls))}, style properties: "
                f"{sorted(STYLE_PROPERTIES)} and 'visible'"
            )

    def remove_attribute(self, el: GpuiElement, attr: str, value: Any):
        name = normalize_attribute(attr)
        if isinstance(el, GpuiWindow):
            el.properties.pop(name, None)
            return
        cls = el.control_class
        if name == "style":
            self._set_style(el, {})
        elif name == "visible":
            self.set_attribute(el, "visible", True)
        elif name in _properties(cls):
            default = _properties(cls)[name]
            el.properties.pop(name, None)
            if el.control is not None:
                self._update_property(el, name, copy.deepcopy(default))
        elif name in STYLE_PROPERTIES:
            style = dict(el.style)
            style.pop(name, None)
            self._set_style(el, style)

    def add_event_listener(self, el: GpuiElement, event_type: str, value: Callable):
        name = normalize_attribute(event_type)
        supported = () if isinstance(el, GpuiWindow) else _events(el.control_class)
        if name not in supported:
            raise ValueError(
                f"<{el.tag}> does not support the '{event_type}' event. "
                f"Supported events: {sorted(supported) or 'none'}"
            )
        el.listeners.setdefault(name, []).append(value)

    def remove_event_listener(self, el: GpuiElement, event_type: str, value: Callable):
        name = normalize_attribute(event_type)
        listeners = el.listeners.get(name, [])
        if value in listeners:
            listeners.remove(value)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _native(item: Any) -> Any:
        if isinstance(item, GpuiElement | GpuiTextElement | GpuiWindow):
            return item.control
        return item

    def _realize(self, el: GpuiElement | GpuiTextElement) -> Control:
        """Construct the gpyui control for the element (once)."""
        if el.control is not None and not el.control.disposed:
            return el.control
        if isinstance(el, GpuiTextElement):
            el.control = gpyui.Label(el.content)
            return el.control
        el.control = self._construct(el)
        return el.control

    def _construct(self, el: GpuiElement) -> Control:
        kwargs = {
            **REQUIRED_ARGUMENTS.get(el.factory, {}),
            **copy.deepcopy(el.properties),
        }
        for event in _events(el.control_class):
            kwargs[f"on_{event}"] = _dispatcher(el, event)
        try:
            control = el.factory(**kwargs)
        except Exception as e:
            raise type(e)(f"Can't create <{el.tag}>: {e}") from e
        if el.style:
            control.style(**el.style)
        if not el.visible:
            control.visible = False
        return control

    def _update_property(self, el: GpuiElement, name: str, value: Any):
        control = el.control
        if _settable(control, name):
            setattr(control, name, value)
        else:
            # Construction-only property: replace the control
            self._rebuild(el)

    def _set_style(self, el: GpuiElement, style: dict[str, Any]):
        removed = el.style.keys() - style.keys()
        el.style = style
        if el.control is None:
            return
        if removed:
            # gpyui merges styles, so removing a style property
            # requires a fresh control
            self._rebuild(el)
        else:
            el.control.style(**style)

    def _rebuild(self, el: GpuiElement):
        """Replace the control of `el` with a new one, constructed with its
        current properties. Keeps the position in the parent and the children."""
        old = el.control
        # Keep native state (e.g. the value of an input) that is not bound
        for name in _properties(el.control_class):
            if name not in el.properties and name in _values(old):
                el.properties[name] = _values(old)[name]
        new = self._construct(el)
        children = old.children if isinstance(old, Column) else ()
        if children:
            old.set_children(())
            new.set_children(children)
        parent = _parent_of(old, self._app)
        if parent is not None:
            siblings = [new if child is old else child for child in parent.children]
            parent.set_children(siblings)
        el.control = new
        old.dispose()

    def _insert_text(self, el: GpuiTextElement, parent: GpuiElement, anchor: Any):
        if "text" not in _properties(parent.control_class):
            raise TypeError(f"<{parent.tag}> does not support text content")
        index = len(parent.text_children)
        if anchor is not None and anchor in parent.text_children:
            index = parent.text_children.index(anchor)
        parent.text_children.insert(index, el)
        el.text_parent = parent
        el.attached = True
        self._sync_text(parent)

    def _sync_text(self, el: GpuiElement):
        text = _joined_text(el)
        el.properties["text"] = text
        if el.control is not None:
            self._update_property(el, "text", text)

    def _schedule_collect(self):
        if self._collect_scheduled:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No loop (not running yet): collect on a later removal
            return
        self._collect_scheduled = True
        loop.call_soon(self._collect)

    def _collect(self):
        """Dispose controls of elements that were removed and not re-inserted."""
        self._collect_scheduled = False
        detached, self._detached = self._detached, []
        for el in detached:
            control = el.control
            if el.attached or control is None or control.disposed:
                continue
            el.control = None
            control.dispose()


# ----------------------------------------------------------------------
# Helpers for introspecting gpyui control classes
# ----------------------------------------------------------------------

_PROPERTIES_CACHE: dict[type, dict[str, Any]] = {}
_EVENTS_CACHE: dict[type, tuple[str, ...]] = {}


def _properties(cls: type) -> dict[str, Any]:
    """Return the properties (and their defaults) a control class accepts."""
    if cls in _PROPERTIES_CACHE:
        return _PROPERTIES_CACHE[cls]
    result: dict[str, Any] = {}
    if isinstance(cls, type) and issubclass(cls, KitControl):
        result = {name: default for name, (default, _) in cls.fields.items()}
        result = {name: val for name, val in result.items() if not name.startswith("_")}
    elif isinstance(cls, type):
        for param in inspect.signature(cls.__init__).parameters.values():
            if param.name in ("self", "children") or param.name.startswith("on_"):
                continue
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            default = param.default
            if default is param.empty:
                default = REQUIRED_ARGUMENTS.get(cls, {}).get(param.name)
            result[param.name] = default
    _PROPERTIES_CACHE[cls] = result
    return result


def _property_type(cls: type, name: str) -> type | None:
    default = _properties(cls).get(name)
    if isinstance(default, bool):
        return bool
    if isinstance(default, int | float):
        return float if isinstance(default, float) else int
    if isinstance(default, str):
        return str
    return None


def _events(cls: type) -> tuple[str, ...]:
    """Return the event names a control class supports."""
    if cls in _EVENTS_CACHE:
        return _EVENTS_CACHE[cls]
    if isinstance(cls, type) and issubclass(cls, KitControl):
        result = tuple(cls.events)
    elif isinstance(cls, type):
        result = tuple(
            name[3:]
            for name in inspect.signature(cls.__init__).parameters
            if name.startswith("on_")
        )
    else:
        result = ()
    _EVENTS_CACHE[cls] = result
    return result


def _values(control: Control) -> dict[str, Any]:
    """Current property values of a control (including native edits)."""
    if isinstance(control, KitControl):
        return {name: getattr(control, name) for name in type(control).fields}
    result = {}
    for name in _properties(type(control)):
        try:
            result[name] = getattr(control, name)
        except AttributeError:
            pass
    return result


def _settable(control: Control, name: str) -> bool:
    """Whether property `name` can be updated on a live control."""
    cls = type(control)
    if isinstance(control, KitControl):
        return name in cls.fields and name not in cls.readonly
    attr = inspect.getattr_static(cls, name, None)
    if isinstance(attr, property):
        return attr.fset is not None
    # Some controls (e.g. TextInput) handle properties in __setattr__
    has_custom_setattr = any("__setattr__" in vars(base) for base in cls.__mro__[:-1])
    return has_custom_setattr and name in _values(control)


def _is_container(native: Any) -> bool:
    if isinstance(native, gpyui.Application):
        return True
    if isinstance(native, KitControl):
        return type(native).container
    return isinstance(native, Column)


def _parent_of(control: Control, app: gpyui.Application | None) -> Any:
    # gpyui does not expose a public parent property
    parent = getattr(control, "_parent", None)
    if parent is None and app is not None and control in app.children:
        return app
    return parent


def _joined_text(el: GpuiElement) -> str:
    return "".join(text.content for text in el.text_children)


def _dispatcher(el: GpuiElement, event: str) -> Callable[[gpyui.Event], None]:
    """Create a gpyui event handler that calls the listeners of `el`.

    Listeners receive the value of the event as argument (for instance the
    new value of a slider), or no arguments for events without a value
    (such as a button click)."""

    def dispatch(gpui_event: gpyui.Event) -> None:
        for listener in list(el.listeners.get(event, ())):
            if gpui_event.value is None:
                listener()
            else:
                listener(gpui_event.value)

    return dispatch


_TRUE = {"", "true", "1", "yes", "on"}
_FALSE = {"false", "0", "no", "off"}


def _coerce(target: type | None, value: Any) -> Any:
    """Coerce static (string) template attributes to the type gpyui expects."""
    if not isinstance(value, str) or target in (None, str):
        return value
    if target is bool:
        lowered = value.strip().lower()
        if lowered in _TRUE:
            return True
        if lowered in _FALSE:
            return False
        return value
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _register_gpyui_controls():
    for name in gpyui.__all__:
        obj = getattr(gpyui, name)
        if isinstance(obj, type) and issubclass(obj, Control) and obj is not Control:
            GpuiRenderer.ELEMENTS.setdefault(normalize_name(name), obj)


_register_gpyui_controls()
