import js

from . import Renderer


class DomRenderer(Renderer):
    """Renderer that renders to a pyodide dom"""

    def create_element(self, type: str) -> dict:
        element = (
            js.window.document.createTextNode("")
            if type == "TEXT_ELEMENT"
            else js.window.document.createElement(type)
        )
        return element

    def insert(self, el, parent, anchor=None):
        if anchor:
            parent.insertBefore(el, anchor)
        else:
            parent.appendChild(el)

    def remove(self, el, parent):
        parent.removeChild(el)

    def set_attribute(self, obj, attr: str, value):
        if obj.nodeType == js.Node.TEXT_NODE:  # and attr == "content":
            obj.nodeValue = value
        else:
            obj.setAttribute(attr, value)

    def remove_attribute(self, obj, attr: str, value):
        obj.removeAttribute(attr)

    def add_event_listener(self, el, event_type, value):
        el.addEventListener(event_type, value)

    def remove_event_listener(self, el, event_type, value):
        el.removeEventListener(event_type, value)
