from collections import defaultdict

from . import Renderer


class DictRenderer(Renderer):
    def create_element(self, type: str) -> dict:
        return {"type": type}

    def insert(self, el, parent):
        children = parent.setdefault("children", [])
        children.append(el)

    def remove(self, el, parent):
        children = parent.get("children", [])
        try:
            children.remove(el)
        except ValueError:
            pass

    def set_attribute(self, obj, attr: str, value):
        obj[attr] = value

    def clear_attribute(self, obj, attr: str, value):
        if attr in obj:
            del obj[attr]

    def add_event_listener(self, el, event_type, value):
        event_listeners = el.setdefault("event_listeners", defaultdict(set))
        event_listeners[event_type].add(value)

    def remove_event_listener(self, el, event_type, value):
        event_listeners = el.get("event_listeners", None)
        if event_listeners:
            event_listeners[event_type].remove(value)
