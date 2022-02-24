from collections import defaultdict

import pygfx as gfx


def create_element(type) -> gfx.WorldObject:
    """Create pygfx element for the given type"""
    if type == "Point":
        # NOTE: geometry and material should preferably be passed through
        # state instead of generated here, because they are resources that
        # can be shared
        obj = gfx.Mesh(gfx.sphere_geometry(), gfx.MeshBasicMaterial())
    if type == "Group":
        obj = gfx.Group()

    def add_event_handler(type, callback):
        """Register an event handler."""
        obj._event_handlers[type].add(callback)

    def handle_event(event):
        """Handle an incoming event."""
        event_type = event.get("event_type")
        for callback in obj._event_handlers[event_type]:
            callback(event)

    def remove_event_handler(type, callback):
        """Unregister an event handler."""
        obj._event_handlers[type].remove(callback)

    if isinstance(obj, gfx.Mesh):
        # Patch the returned object to be able to handle events
        setattr(obj, "_event_handlers", defaultdict(set))
        setattr(obj, "add_event_handler", add_event_handler)
        setattr(obj, "handle_event", handle_event)
        setattr(obj, "remove_event_handler", remove_event_handler)
    return obj


def set_attribute(dom, key, value):
    # TODO: set_attribute and clear_attribute should all be done by a Pygfx renderer
    if key == "color":
        dom.material.color = value
        return

    if isinstance(value, list) and len(value) == 3:
        value = gfx.linalg.Vector3(*value)
    setattr(dom, key, value)


def clear_attribute(dom, key, value):
    # TODO: set_attribute and clear_attribute should all be done by a Pygfx renderer
    # TODO: define some kind of defaults for pygfx objects?
    if key == "color":
        dom.material.color = (1, 1, 1, 1)
        return

    if isinstance(value, list) and len(value) == 3:
        value = gfx.linalg.Vector3()
    else:
        value = None
    setattr(dom, key, value)
