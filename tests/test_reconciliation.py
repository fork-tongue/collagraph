from weakref import ref

from observ import reactive
import pytest

from pygui import create_element as h, PyGui
from pygui.renderers import Renderer


class CustomElement:
    def __init__(self, *args, type=None, **kwargs):
        super().__setattr__(
            "_data",
            {
                "type": type,
                "children": [],
                **kwargs,
            },
        )

    def __getattr__(self, name):
        if name.startswith("_"):
            return super().__getattr__(name)
        return self._data[name]

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        self._data[name] = value


class CustomElementRenderer(Renderer):
    def create_element(self, type):
        obj = CustomElement(type=type)
        return obj

    def insert(self, el, parent):
        parent.children.append(el)

    def remove(self, el, parent):
        try:
            parent.children.remove(el)
        except ValueError:
            pass

    def set_attribute(self, el, attr: str, value):
        setattr(el, attr, value)

    def clear_attribute(self, el, attr: str, value):
        delattr(el, attr)

    def add_event_listener(self, el, event_type, value):
        return NotImplemented

    def remove_event_listener(self, el, event_type, value):
        return NotImplemented


@pytest.mark.xfail
def test_reconcile_by_key():
    states = [
        ([1, 2, 3], [3, 1, 2]),  # shift right
        ([1, 2, 3], [2, 3, 1]),  # shift left
        ([1, 2, 3], [1, 3]),  # remove from middle
        ([1, 2, 3], [2, 3]),  # remove first
        ([1, 2, 3], [1, 2]),  # remove last
        ([1, 2, 3], [3, 2, 1]),  # reverse order
    ]

    def Items(props):
        return h(
            "items",
            props,
            *[h("item", {"content": item}) for item in props["items"]],
        )

    renderer = CustomElementRenderer()
    gui = PyGui(renderer=renderer, sync=True)
    container = CustomElement()
    container.type = "root"
    container.children = []

    for before, after in states:
        state = reactive({"items": before})
        element = h(Items, state)

        gui.render(element, container)

        items = container.children[0]

        for idx, val in enumerate(before):
            item = items.children[idx]
            assert item.content == val

        children_refs = [ref(x) for x in items.children]

        state["items"] = after

        for idx, val in enumerate(after):
            item = items.children[idx]
            assert item.content == val

            prev_idx = before.index(val)
            assert item is children_refs[prev_idx]()
