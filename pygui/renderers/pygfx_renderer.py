from collections import defaultdict

import pygfx as gfx

from . import Renderer


class MeshEvents(gfx.Mesh):
    """Custom subclass of gfx.Mesh to enable handling of events."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_handlers = defaultdict(set)

    def add_event_handler(self, type, callback):
        """Register an event handler."""
        self._event_handlers[type].add(callback)

    def handle_event(self, event):
        """Handle an incoming event."""
        event_type = event.get("event_type")
        for callback in self._event_handlers[event_type]:
            callback(event)

    def remove_event_handler(self, type, callback):
        """Unregister an event handler."""
        self._event_handlers[type].remove(callback)


class PygfxRenderer(Renderer):
    def insert(
        self,
        el: gfx.WorldObject,
        parent: gfx.WorldObject,
        anchor: gfx.WorldObject = None,
    ):
        parent.add(el, before=anchor)

    def remove(self, el: gfx.WorldObject, parent: gfx.WorldObject):
        parent.remove(el)

    def create_element(self, type: str) -> gfx.WorldObject:
        """Create pygfx element for the given type"""
        if type == "Point":
            # NOTE: geometry and material should preferably be passed through
            # state instead of generated here, because they are resources that
            # can be shared
            obj = MeshEvents(gfx.sphere_geometry(), gfx.MeshPhongMaterial())
        if type == "Group":
            obj = gfx.Group()
        if type == "Mesh":
            obj = MeshEvents()
        return obj

    def set_attribute(self, obj, attr, value):
        if attr == "color":
            obj.material.color = value
            return

        if hasattr(value, "__len__") and len(value) == 3:
            value = gfx.linalg.Vector3(*value)
        setattr(obj, attr, value)

    def remove_attribute(self, obj, attr, value):
        # TODO: define some kind of defaults for pygfx objects?
        if attr == "color":
            obj.material.color = (1, 1, 1, 1)
            return

        if hasattr(value, "__len__") and len(value) == 3:
            value = gfx.linalg.Vector3()
        else:
            value = None
        setattr(obj, attr, value)

    def add_event_listener(self, el, event_type, value):
        el.add_event_handler(event_type, value)

    def remove_event_listener(self, el, event_type, value):
        el.remove_event_handler(event_type, value)
