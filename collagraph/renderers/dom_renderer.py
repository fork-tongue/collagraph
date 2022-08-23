import js

from . import Renderer


class DomRenderer(Renderer):
    """Renderer that renders to a pyodide dom"""

    def create_element(self, type: str) -> dict:
        return js.window.document.createElement(type)

    def create_text_element(self):
        return js.window.document.createTextNode("")

    def insert(self, el, parent, anchor=None):
        if anchor is not None:
            parent.insertBefore(el, anchor)
        else:
            parent.appendChild(el)

    def remove(self, el, parent):
        parent.removeChild(el)

    def set_element_text(self, el, value):
        el.textContent = value

    def set_attribute(self, el, attr: str, value):
        el.setAttribute(attr, value)

    def remove_attribute(self, el, attr: str, value):
        el.removeAttribute(attr)

    def add_event_listener(self, el, event_type, value):
        el.addEventListener(event_type, value)

    def remove_event_listener(self, el, event_type, value):
        el.removeEventListener(event_type, value)
