from observ import reactive
import pytest

from collagraph import (
    Collagraph,
    Component,
    create_element as h,
    DictRenderer,
    EventLoopType,
)


class Counter(Component):
    def __init__(self, props):
        super().__init__(props)
        self.state["count"] = self.props.get("count", 0)
        self.state["step_size"] = self.props.get("step_size", 1)

    def bump(self):
        self.state["count"] += self.state["step_size"]

    def render(self):
        return h("counter", {"count": self.state["count"], "on_bump": self.bump})

    def __repr__(self):
        return f"<Counter {self.state['count']}>"


def test_component_class():
    counter = Counter({})

    assert counter.state["count"] == 0

    counter.bump()

    assert counter.state["count"] == 1


def test_component_events():
    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"count": 0})
    element = h(Counter, state)

    gui.render(element, container)

    counter = container["children"][0]
    assert counter["type"] == "counter"
    assert counter["attrs"]["count"] == 0

    for i in range(1, 6):
        # Update state by triggering all listeners, which should trigger a re-render
        for listener in counter["handlers"]["bump"]:
            listener()

        assert counter["attrs"]["count"] == i

    # Assert that global state hasn't been touched
    assert state["count"] == 0


def test_component_basic_lifecycle():
    class SpecialCounter(Counter):
        lifecycle = []

        def __init__(self, props):
            super().__init__(props)

        def mounted(self):
            super().mounted()
            SpecialCounter.lifecycle.append(f"{self.props['name']}:mounted")

        def updated(self):
            super().updated()
            SpecialCounter.lifecycle.append(f"{self.props['name']}:updated")

        def before_unmount(self):
            super().before_unmount()
            SpecialCounter.lifecycle.append(f"{self.props['name']}:before_unmount")

        def render(self):
            return h(
                "counter",
                {**self.props, "count": self.state["count"], "on_bump": self.bump},
                *[h(SpecialCounter, props) for props in self.props.get("subs", [])],
            )

        def __repr__(self):
            return f"<SpecialCounter({self.props['name']}) {self.state['count']}>"

    def Counters(props):
        return h(
            "counters", {}, *[h(SpecialCounter, prop) for prop in props["counters"]]
        )

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive(
        {
            "counters": [
                {
                    "name": "parent",
                    "subs": [
                        {"name": "child"},
                    ],
                },
            ]
        }
    )

    element = h(Counters, state)

    assert SpecialCounter.lifecycle == []

    gui.render(element, container)

    parent_counter = container["children"][0]["children"][0]
    child_counter = container["children"][0]["children"][0]["children"][0]
    assert parent_counter["attrs"]["name"] == "parent"
    assert child_counter["attrs"]["name"] == "child"
    assert parent_counter["attrs"]["count"] == 0
    assert child_counter["attrs"]["count"] == 0

    assert SpecialCounter.lifecycle == [
        "child:mounted",
        "parent:mounted",
    ]

    # Reset lifecycle
    SpecialCounter.lifecycle = []

    for i in range(1, 6):
        # Update state by triggering all listeners, which should trigger a re-render
        for listener in parent_counter["handlers"]["bump"]:
            listener()

        assert parent_counter["attrs"]["count"] == i
        assert SpecialCounter.lifecycle == ["parent:updated"]
        SpecialCounter.lifecycle = []

    for i in range(1, 8):
        # Update state by triggering all listeners, which should trigger a re-render
        for listener in child_counter["handlers"]["bump"]:
            listener()

        assert child_counter["attrs"]["count"] == i
        assert SpecialCounter.lifecycle == ["child:updated"]
        SpecialCounter.lifecycle = []

    state["counters"] = []

    assert len(container["children"][0]["children"]) == 0

    assert SpecialCounter.lifecycle == [
        "parent:before_unmount",
        "child:before_unmount",
    ]


def test_component_without_render_method():
    class Faulty(Component):
        pass

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({})

    element = h(Faulty, state)

    with pytest.raises(TypeError):
        gui.render(element, container)


def test_component_props_update():
    class Counter(Component):
        updates = 0

        def updated(self):
            Counter.updates += 1

        def render(self):
            return h("Counter", {**self.props})

    state = reactive({"prop": False})

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    element = h(Counter, state)
    gui.render(element, container)

    assert Counter.updates == 0
    assert container["children"][0]["attrs"]["prop"] is False

    state["prop"] = True

    assert Counter.updates == 1
    assert container["children"][0]["attrs"]["prop"] is True


def test_component_props_update_elaborate():
    """
    Test that 'computed' values are updated on the component.
    'Computed' values are values that are not coming from reactive
    state directly, for instance a function that returns a new list.
    """

    class Example(Component):
        def render(self):
            return h("foo", {"value": self.props["selection"]})

    def App(props):
        # Function
        def selected_items():
            return [
                item
                for key, item in props["items"].items()
                if key in props["selected_items"]
            ]

        return h(Example, {"selection": selected_items()})

    state = reactive(
        {
            "items": {"a": "A"},
            "selected_items": ["a"],
        }
    )

    container = {"type": "root"}
    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    gui.render(h(App, state), container)

    foo = container["children"][0]
    assert foo["type"] == "foo"
    assert foo["attrs"]["value"] == ["A"]

    state["selected_items"] = []

    assert foo["attrs"]["value"] == []


def test_component_props_deep_update():
    class Counter(Component):
        updates = 0

        def updated(self):
            Counter.updates += 1

        def render(self):
            # Note that the array is unpacked with a star expression
            # into a new list, in order to make sure that any change
            # to the array will be picked up. Because by default, the
            # attributes are not deep watched but shallow. Unpacking
            # explicitely adds dependencies on the unpacked values.
            return h("Counter", {"prop": [*self.props["prop"]]})

    state = reactive({"prop": [0, 1]})

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    element = h(Counter, state)
    gui.render(element, container)

    assert Counter.updates == 0
    assert container["children"][0]["attrs"]["prop"] == [0, 1]

    state["prop"].append(2)

    assert container["children"][0]["attrs"]["prop"] == [0, 1, 2]
    assert Counter.updates == 1


def test_component_props_deep_update_without_unpack():
    class Counter(Component):
        updates = 0

        def updated(self):
            Counter.updates += 1

        def render(self):
            return h("Counter", self.props)

    state = reactive({"prop": [0, 1]})

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    element = h(Counter, state)
    gui.render(element, container)

    assert Counter.updates == 0
    # Note that the DictRenderer sets the original value
    assert container["children"][0]["attrs"]["prop"] == [0, 1]
    assert container["children"][0]["attrs"]["prop"] is state["prop"]

    # So here we are appending an extra item, but this change is not detected
    # by Collagraph, because it watches the props shallow, not deep
    state["prop"].append(2)

    assert Counter.updates == 0
    # But because the value is passed as reference, we see can still see the
    # added element. If the DictRenderer would have made a copy, this value
    # would not have been the same, so this behaviour is highly dependent
    # on the type of renderer being used.
    assert container["children"][0]["attrs"]["prop"] == [0, 1, 2]


def test_component_element():
    component = None

    class SpecialComponent(Component):
        def mounted(self):
            nonlocal component
            component = self

        def render(self):
            return h("special")

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"count": 0})
    element = h(SpecialComponent, state)

    gui.render(element, container)

    assert component is not None
    assert isinstance(component, SpecialComponent)
    assert component.element is container["children"][0]


def test_component_overwrite_props_and_state():
    class OverwriteState(Component):
        def __init__(self, props):
            super().__init__(props)
            self.state = {}

        def render(self):
            return h

    with pytest.raises(RuntimeError):
        _ = OverwriteState({})

    class OverwriteProps(Component):
        def __init__(self, props):
            super().__init__(props)
            self.props = {}

        def render(self):
            return h

    with pytest.raises(RuntimeError):
        _ = OverwriteProps({})
