from collections import defaultdict

from . import Renderer


class DictRenderer(Renderer):
    """Renderer that renders to a simple dict object
    which (may) contain the following keys:
    * type: str
    * children: list
    * attributes: dict
    * event_listeners: defaultdict(set)
    * text: str (only for TEXT_ELEMENT items)
    """

    def create_element(self, type: str) -> dict:
        return {"type": type}

    def create_text_element(self):
        return {"type": "TEXT_ELEMENT"}

    def insert(self, el, parent, anchor=None):
        children = parent.setdefault("children", [])
        anchor_idx = children.index(anchor) if anchor else len(children)
        children.insert(anchor_idx, el)

    def remove(self, el, parent):
        children = parent["children"]
        children.remove(el)

    def set_element_text(self, el: dict, value: str):
        el["text"] = value

    def set_attribute(self, obj, attr: str, value):
        attributes = obj.setdefault("attrs", {})
        attributes[attr] = value

    def remove_attribute(self, obj, attr: str, value):
        attributes = obj["attrs"]
        if attr in attributes:
            del attributes[attr]

    def add_event_listener(self, el, event_type, value):
        event_listeners = el.setdefault("handlers", defaultdict(set))
        event_listeners[event_type].add(value)

    def remove_event_listener(self, el, event_type, value):
        event_listeners = el.get("handlers", None)
        if event_listeners:
            event_listeners[event_type].remove(value)
