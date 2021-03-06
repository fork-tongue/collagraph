from weakref import ref

from observ import reactive

from collagraph import Collagraph, create_element as h, EventLoopType
from collagraph.renderers import Renderer


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

    def __repr__(self):
        attributes = ", ".join(
            [
                f"{attr}='{self._data[attr]}'"
                for attr in self._data
                if attr not in ["type", "children"]
            ]
        )
        return f"<{self.type} {attributes}>"


class CustomElementRenderer(Renderer):
    def create_element(self, type):
        obj = CustomElement(type=type)
        return obj

    def insert(self, el, parent, anchor=None):
        idx = parent.children.index(anchor) if anchor else len(parent.children)
        parent.children.insert(idx, el)

    def remove(self, el, parent):
        parent.children.remove(el)

    def set_attribute(self, el, attr: str, value):
        setattr(el, attr, value)

    def remove_attribute(self, el, attr: str, value):
        delattr(el, attr)

    def add_event_listener(self, el, event_type, value):
        raise NotImplementedError

    def remove_event_listener(self, el, event_type, value):
        raise NotImplementedError

    def create_text_element(self):
        raise NotImplementedError

    def set_element_text(self):
        raise NotImplementedError


def test_reconcile_by_key():
    states = [
        (["a", "b", "c"], ["c", "a", "b"], "shift right"),  # shift right
        (["a", "b", "c"], ["b", "c", "a"], "shift left"),  # shift left
        (["a", "b", "c"], ["c", "b", "a"], "reverse order"),  # reverse order
        (["a", "b", "c"], ["a", "b"], "remove last"),  # remove last
        (["a", "b", "c"], ["a", "c"], "remove from middle"),  # remove from middle
        (["a", "b", "c"], ["b", "c"], "remove first"),  # remove first
        (["a", "b", "c"], ["a", "b", "c", "d"], "add last"),  # add last
        (["a", "b", "c"], ["a", "b", "d", "c"], "add in middle"),  # add in middle
        (["a", "b", "c"], ["d", "a", "b", "c"], "add begin"),  # add begin
        (["a", "b", "c", "d"], ["e", "f"], "replace completely"),  # replace completely
    ]

    def Items(props):
        return h(
            "items",
            props,
            *[h("item", {"key": item, "content": item}) for item in props["items"]],
        )

    renderer = CustomElementRenderer()

    for before, after, name in states:
        gui = Collagraph(renderer=renderer, event_loop_type=EventLoopType.SYNC)
        container = CustomElement()
        container.type = "root"
        container.children = []
        state = reactive({"items": before})
        element = h(Items, state)

        gui.render(element, container)

        items = container.children[0]

        for idx, val in enumerate(before):
            item = items.children[idx]
            assert item.content == val, name

        children_refs = [ref(x) for x in items.children]

        state["items"] = after

        for idx, val in enumerate(after):
            item = items.children[idx]
            assert item.content == val, name

            try:
                prev_idx = before.index(val)
                assert item is children_refs[prev_idx](), name
            except ValueError:
                pass

        assert len(after) == len(items.children), name
