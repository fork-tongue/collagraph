"""Tests for the pure-Python view API (collagraph.dsl)."""

import pytest
from observ import reactive

import collagraph as cg
from collagraph import Collagraph, EventLoopType, h
from collagraph.renderers import DictRenderer


def render(component_class, state=None):
    """Render the given component class into a fresh container."""
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(component_class, container, state=state)
    return gui, container


def test_counter():
    class Counter(cg.Component):
        def init(self):
            self.state["count"] = 0

        def bump(self):
            self.state["count"] += 1

        def view(self):
            with h.widget():
                h.label(text=lambda: f"Count: {self.state['count']}")
                h.button("bump", on_clicked=self.bump)

    _, container = render(Counter)

    widget = container["children"][0]
    label, button = widget["children"]
    assert label["attrs"]["text"] == "Count: 0"
    assert button["children"][0]["text"] == "bump"

    # Trigger the clicked event handler like a real button would
    for handler in button["handlers"]["clicked"]:
        handler()

    assert label["attrs"]["text"] == "Count: 1"


def test_static_and_bound_attributes():
    class App(cg.Component):
        def view(self):
            h.label(
                text="static",
                maximum_size=(40, 40),
                other=lambda: self.props["value"] * 2,
            )

    state = reactive({"value": 3})
    _, container = render(App, state=state)

    label = container["children"][0]
    assert label["attrs"]["text"] == "static"
    assert label["attrs"]["maximum_size"] == (40, 40)
    assert label["attrs"]["other"] == 6

    state["value"] = 5

    assert label["attrs"]["other"] == 10


def test_bind_dict():
    class App(cg.Component):
        def view(self):
            h.label(bind=lambda: self.props["attrs"])

    state = reactive({"attrs": {"text": "foo", "height": 100}})
    _, container = render(App, state=state)

    label = container["children"][0]
    assert label["attrs"]["text"] == "foo"
    assert label["attrs"]["height"] == 100

    state["attrs"]["text"] = "bar"

    assert label["attrs"]["text"] == "bar"

    # Removing a key removes the attribute
    del state["attrs"]["height"]

    assert "height" not in label["attrs"]


def test_conditional_chain():
    class App(cg.Component):
        def view(self):
            with h.widget():
                h.label(text="before")
                with cg.when(lambda: self.props["status"] == "loading"):
                    h.label(text="Loading…")
                with cg.elif_(lambda: self.props["status"] == "error"):
                    h.label(text="Error!")
                    h.label(text="Please retry")
                with cg.otherwise():
                    h.label(text="Ready")
                h.label(text="after")

    state = reactive({"status": "loading"})
    _, container = render(App, state=state)

    widget = container["children"][0]

    def texts():
        return [child["attrs"]["text"] for child in widget["children"]]

    assert texts() == ["before", "Loading…", "after"]

    state["status"] = "error"

    # A branch can render multiple children
    assert texts() == ["before", "Error!", "Please retry", "after"]

    state["status"] = "done"

    assert texts() == ["before", "Ready", "after"]

    state["status"] = "loading"

    assert texts() == ["before", "Loading…", "after"]


def test_two_independent_conditions():
    class App(cg.Component):
        def view(self):
            with h.widget():
                with cg.when(lambda: self.props["a"]):
                    h.label(text="a")
                with cg.when(lambda: self.props["b"]):
                    h.label(text="b")

    state = reactive({"a": True, "b": True})
    _, container = render(App, state=state)

    widget = container["children"][0]
    assert [child["attrs"]["text"] for child in widget["children"]] == ["a", "b"]

    # Both conditions operate independently (no when/elif_ chain)
    state["a"] = False

    assert [child["attrs"]["text"] for child in widget["children"]] == ["b"]


def test_each_unkeyed():
    class App(cg.Component):
        def view(self):
            with h.widget():

                @cg.each(lambda: self.props["items"])
                def _(item):
                    h.label(text=lambda: item())

    state = reactive({"items": ["a", "b"]})
    _, container = render(App, state=state)

    widget = container["children"][0]

    def texts():
        return [child["attrs"]["text"] for child in widget["children"]]

    assert texts() == ["a", "b"]

    state["items"].append("c")

    assert texts() == ["a", "b", "c"]

    state["items"].pop(0)

    assert texts() == ["b", "c"]


def test_each_multiple_loop_variables():
    class App(cg.Component):
        def view(self):
            with h.widget():

                @cg.each(lambda: enumerate(self.props["items"]))
                def _(index, item):
                    h.label(text=lambda: f"{index()}: {item()}")

    state = reactive({"items": ["a", "b"]})
    _, container = render(App, state=state)

    widget = container["children"][0]
    texts = [child["attrs"]["text"] for child in widget["children"]]
    assert texts == ["0: a", "1: b"]


def test_each_keyed_reuses_elements():
    class App(cg.Component):
        def view(self):
            with h.widget():

                @cg.each(
                    lambda: self.props["items"],
                    key=lambda item: item["id"],
                )
                def _(item):
                    h.label(text=lambda: item()["text"])

    state = reactive(
        {
            "items": [
                {"id": 1, "text": "one"},
                {"id": 2, "text": "two"},
                {"id": 3, "text": "three"},
            ]
        }
    )
    _, container = render(App, state=state)

    widget = container["children"][0]

    def texts():
        return [child["attrs"]["text"] for child in widget["children"]]

    assert texts() == ["one", "two", "three"]
    elements_by_text = {
        child["attrs"]["text"]: id(child) for child in widget["children"]
    }

    # Reverse the list: elements should be moved, not recreated
    state["items"].reverse()

    assert texts() == ["three", "two", "one"]
    for child in widget["children"]:
        assert id(child) == elements_by_text[child["attrs"]["text"]]


def test_each_with_events():
    """Port of the todo_list.cgx example."""
    clicked = []

    class TodoList(cg.Component):
        def clicked(self, item):
            self.emit("clicked", item)

        def view(self):
            with h.widget():

                @cg.each(lambda: self.props["items"])
                def _(item):
                    with h.widget():
                        h.button(
                            text="✔️",
                            on_clicked=lambda: self.clicked(item()),
                        )
                        h.label(text=item)

    class App(cg.Component):
        def view(self):
            h(TodoList, items=lambda: self.props["items"], on_clicked=clicked.append)

    state = reactive({"items": ["groceries", "dishes"]})
    _, container = render(App, state=state)

    rows = container["children"][0]["children"]
    assert [row["children"][1]["attrs"]["text"] for row in rows] == [
        "groceries",
        "dishes",
    ]

    button = rows[1]["children"][0]
    for handler in button["handlers"]["clicked"]:
        handler()

    assert clicked == ["dishes"]


def test_component_props_and_events():
    class Child(cg.Component):
        def view(self):
            h.button(
                text=lambda: self.props["label"],
                on_clicked=lambda: self.emit("pressed", self.props["label"]),
            )

    pressed = []

    class App(cg.Component):
        def view(self):
            h(Child, label=lambda: self.props["name"], on_pressed=pressed.append)

    state = reactive({"name": "foo"})
    _, container = render(App, state=state)

    button = container["children"][0]
    assert button["attrs"]["text"] == "foo"

    state["name"] = "bar"

    assert button["attrs"]["text"] == "bar"

    for handler in button["handlers"]["clicked"]:
        handler()

    assert pressed == ["bar"]


def test_slots():
    """Port of the slots template example."""

    class Layout(cg.Component):
        def view(self):
            with h.widget():
                with h.widget(name="header"):
                    with cg.slot("header"):
                        h.label(text="fallback header")
                with h.widget(name="content"):
                    cg.slot()
                with h.widget(name="footer"):
                    with cg.slot("footer"):
                        h.label(text="fallback footer")

    class App(cg.Component):
        def view(self):
            with h(Layout):
                with cg.fill("header"):
                    h.label(text="header content")
                h.label(text="content")
                h.label(text="even more content")

    _, container = render(App)

    layout = container["children"][0]
    header, content, footer = layout["children"]

    assert [child["attrs"]["text"] for child in header["children"]] == [
        "header content"
    ]
    # Content without an explicit fill() ends up in the default slot
    assert [child["attrs"]["text"] for child in content["children"]] == [
        "content",
        "even more content",
    ]
    # No content provided for the footer slot: fallback is rendered
    assert [child["attrs"]["text"] for child in footer["children"]] == [
        "fallback footer"
    ]


def test_refs():
    class App(cg.Component):
        def view(self):
            h.label(ref="label", text="referenced")

    gui, container = render(App)

    component = gui.fragment.component
    # == instead of `is`: refs is a reactive dict, reads return a proxy
    assert component.refs["label"] == container["children"][0]


def test_dynamic_component():
    class Foo(cg.Component):
        def view(self):
            h.label(text="foo")

    class Bar(cg.Component):
        def view(self):
            h.label(text="bar")

    class App(cg.Component):
        def view(self):
            cg.dynamic(lambda: Foo if self.props["foo"] else Bar)

    state = reactive({"foo": True})
    _, container = render(App, state=state)

    assert container["children"][0]["attrs"]["text"] == "foo"

    state["foo"] = False

    assert container["children"][0]["attrs"]["text"] == "bar"


def test_when_inside_each():
    class App(cg.Component):
        def view(self):
            with h.widget():

                @cg.each(lambda: self.props["items"])
                def _(item):
                    with cg.when(lambda: item()["done"]):
                        h.label(text=lambda: f"{item()['text']} ✔")
                    with cg.otherwise():
                        h.label(text=lambda: item()["text"])

    state = reactive(
        {
            "items": [
                {"text": "groceries", "done": False},
                {"text": "dishes", "done": True},
            ]
        }
    )
    _, container = render(App, state=state)

    widget = container["children"][0]

    def texts():
        return [child["attrs"]["text"] for child in widget["children"]]

    assert texts() == ["groceries", "dishes ✔"]

    state["items"][0]["done"] = True

    assert texts() == ["groceries ✔", "dishes ✔"]


def test_eager_read_warning():
    class App(cg.Component):
        def init(self):
            self.state["count"] = 0

        def view(self):
            # Bug: reads state during view build, bakes in the value
            h.label(text=f"Count: {self.state['count']}")

    with pytest.warns(UserWarning, match="Reactive value read during view build"):
        render(App)


def test_eager_read_warning_in_each():
    class App(cg.Component):
        def view(self):
            @cg.each(lambda: self.props["items"])
            def _(item):
                # Bug: reads the item getter during build
                h.label(text=item())

    state = reactive({"items": ["a"]})
    with pytest.warns(UserWarning, match="Reactive value read during view build"):
        render(App, state=state)


def test_elif_without_when_raises():
    class App(cg.Component):
        def view(self):
            with cg.elif_(lambda: True):
                h.label(text="nope")

    with pytest.raises(RuntimeError, match="must directly follow"):
        render(App)


def test_h_outside_view_raises():
    with pytest.raises(RuntimeError, match="No view is being built"):
        h.label(text="nope")


def test_no_view_and_no_template_raises():
    class App(cg.Component):
        pass

    with pytest.raises(NotImplementedError, match="neither a template"):
        render(App)
