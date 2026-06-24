import warnings
from typing import Any, Callable
from weakref import ref

import pygfx as gfx

from . import Renderer

ELEMENT_TYPE_CACHE = {}
DEFAULT_ATTR_CACHE = {}


class _TextElementProxy(gfx.WorldObject):
    def __init__(self):
        super().__init__()
        self._cg_content = ""
        self._cg_parent_text_ref = None

    @property
    def _cg_parent_text(self) -> gfx.Text | None:
        if self._cg_parent_text_ref is None:
            return None
        return self._cg_parent_text_ref()

    def _cg_set_parent_text(self, parent: gfx.Text | None):
        self._cg_parent_text_ref = ref(parent) if parent else None


class PygfxRenderer(Renderer):
    """Renderer for Pygfx objects"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_change_handlers = set()

    def add_on_change_handler(self, handler: Callable):
        self._on_change_handlers.add(handler)

    def remove_on_change_handler(self, handler: Callable):
        self._on_change_handlers.remove(handler)

    def _trigger(self):
        for handler in self._on_change_handlers:
            handler()

    def register_asyncio(self):
        import asyncio

        from PySide6.QtAsyncio import QAsyncioEventLoopPolicy

        policy = asyncio.get_event_loop_policy()
        if not isinstance(policy, QAsyncioEventLoopPolicy):
            asyncio.set_event_loop_policy(QAsyncioEventLoopPolicy())

    def create_element(self, type: str) -> gfx.WorldObject:
        """Create pygfx element for the given type"""
        type = type.lower().replace("-", "").replace("_", "")
        if type == "textelement":
            self._trigger()
            return _TextElementProxy()

        if element_type := ELEMENT_TYPE_CACHE.get(type):
            self._trigger()
            return element_type()

        attrs = dir(gfx)
        for attr in attrs:
            if attr.lower() == type:
                element_type = getattr(gfx, attr)
                ELEMENT_TYPE_CACHE[type] = element_type
                self._trigger()
                return element_type()

        raise ValueError(f"Can't create element of type: {type}")

    def create_text_element(self):
        raise NotImplementedError

    def insert(
        self,
        el: gfx.WorldObject,
        parent: gfx.WorldObject,
        anchor: gfx.WorldObject | None = None,
    ):
        is_text_proxy = isinstance(el, _TextElementProxy)
        try:
            parent.add(el, before=anchor)
        except ValueError:
            warnings.warn(f"Could not find anchor in {parent}")
            parent.add(el)

        if is_text_proxy and isinstance(parent, gfx.Text):
            el._cg_set_parent_text(parent)
            self._sync_text_from_proxy_children(parent)
            return

        self._trigger()

    def remove(self, el: gfx.WorldObject, parent: gfx.WorldObject):
        parent.remove(el)

        if isinstance(el, _TextElementProxy):
            if isinstance(parent, gfx.Text):
                self._sync_text_from_proxy_children(parent)
            el._cg_set_parent_text(None)
            return

        self._trigger()

    def set_element_text(self, el, value: str):
        if isinstance(el, _TextElementProxy):
            el._cg_content = value
            if parent := el._cg_parent_text:
                self._sync_text_from_proxy_children(parent)
            return

        raise NotImplementedError

    def _sync_text_from_proxy_children(self, parent: gfx.Text):
        content = "".join(
            child._cg_content
            for child in parent.children
            if isinstance(child, _TextElementProxy)
        )
        parent.set_text(content)
        self._trigger()

    def set_attribute(self, el: gfx.WorldObject, attr: str, value: Any):
        key = f"{type(el).__name__}.{attr}"

        # Split the given attr on dots to allow for
        # local.position for instance to be set
        *attrs, attr = attr.split(".")
        for attribute in attrs:
            el = getattr(el, attribute)

        if isinstance(el, _TextElementProxy) and attr == "content":
            self.set_element_text(el, value)
            return

        if isinstance(el, gfx.Text):
            if attr == "text":
                el.set_text(value)
                self._trigger()
                return
            if attr == "markdown":
                el.set_markdown(value)
                self._trigger()
                return

        if key not in DEFAULT_ATTR_CACHE:
            if hasattr(el, attr):
                default_value = getattr(el, attr)
                if hasattr(default_value, "copy"):
                    DEFAULT_ATTR_CACHE[key] = default_value.copy()
                else:
                    DEFAULT_ATTR_CACHE[key] = default_value

        setattr(el, attr, value)
        self._trigger()

    def remove_attribute(self, el: gfx.WorldObject, attr: str, value: Any):
        key = f"{type(el).__name__}.{attr}"

        # Split the given attr on dots to allow for
        # local.position for instance to be set
        *attrs, attr = attr.split(".")
        for attribute in attrs:
            el = getattr(el, attribute)

        if key in DEFAULT_ATTR_CACHE:
            default_value = DEFAULT_ATTR_CACHE[key]
            if hasattr(default_value, "copy"):
                val = default_value.copy()
            else:
                val = default_value
            setattr(el, attr, val)
        else:
            delattr(el, attr)
        self._trigger()

    def add_event_listener(self, el, event_type, value):
        el.add_event_handler(value, event_type)

    def remove_event_listener(self, el, event_type, value):
        el.remove_event_handler(value, event_type)
