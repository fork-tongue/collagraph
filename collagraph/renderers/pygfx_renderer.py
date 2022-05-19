import pygfx as gfx

from . import Renderer

ELEMENT_TYPE_CACHE = {}


class PygfxRenderer(Renderer):
    """Renderer for Pygfx objects"""

    def create_element(self, type: str) -> gfx.WorldObject:
        """Create pygfx element for the given type"""
        type = type.lower()
        if element_type := ELEMENT_TYPE_CACHE.get(type):
            return element_type()

        attrs = dir(gfx)
        for attr in attrs:
            if attr.lower() == type:
                element_type = getattr(gfx, attr)
                ELEMENT_TYPE_CACHE[type] = element_type
                return element_type()

        raise ValueError(f"Can't create element of type: {type}")

    def insert(
        self,
        el: gfx.WorldObject,
        parent: gfx.WorldObject,
        anchor: gfx.WorldObject = None,
    ):
        parent.add(el, before=anchor)

    def remove(self, el: gfx.WorldObject, parent: gfx.WorldObject):
        parent.remove(el)

    def set_attribute(self, obj, attr, value):
        if isinstance(obj, gfx.WorldObject):
            if attr in {"position", "scale"}:
                value = gfx.linalg.Vector3(*value)
            elif attr == "rotation":
                value = gfx.linalg.Quaternion(*value)
            elif attr == "matrix":
                value = gfx.linalg.Matrix4(*value)

        setattr(obj, attr, value)

    def remove_attribute(self, obj, attr, value):
        raise NotImplementedError

    def add_event_listener(self, el, event_type, value):
        el.add_event_handler(value, event_type)

    def remove_event_listener(self, el, event_type, value):
        el.remove_event_handler(value, event_type)
