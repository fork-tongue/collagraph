from observ import reactive

from collagraph import Collagraph, Component, create_element as h, EventLoopType


class Counter(Component):
    def __init__(self, props):
        super().__init__(props)
        self.count = props.get("count", 0)

    def bump(self):
        self.count += 1

    def render(self):
        return h("counter", {"count": self.count, "onBump": self.bump})

    def __repr__(self):
        return f"<Counter {self.count}>"


def test_component_class():
    counter = Counter({})

    assert counter.count == 0

    counter.bump()

    assert counter.count == 1


def test_component_events():
    gui = Collagraph(event_loop_type=EventLoopType.SYNC)
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
            self.name = props["name"]
            self.children = props.get("children", [])

        def before_mount(self):
            SpecialCounter.lifecycle.append(f"{self.name}:before_mount")

        def mounted(self):
            SpecialCounter.lifecycle.append(f"{self.name}:mounted")

        def before_update(self):
            SpecialCounter.lifecycle.append(f"{self.name}:before_update")

        def updated(self):
            SpecialCounter.lifecycle.append(f"{self.name}:updated")

        def before_unmount(self):
            SpecialCounter.lifecycle.append(f"{self.name}:before_unmount")

        def unmounted(self):
            SpecialCounter.lifecycle.append(f"{self.name}:unmounted")

        def render(self):
            return h(
                "counter",
                {"count": self.count, "onBump": self.bump},
                *[h(SpecialCounter, props) for props in self.children],
            )

        def __repr__(self):
            return f"<Counter({self.name}) {self.count}>"

    def Counters(props):
        props.setdefault("counters", [])

        return h(
            "counters", props, *[h(SpecialCounter, prop) for prop in props["counters"]]
        )

    gui = Collagraph(event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive(
        {
            "counters": [
                {
                    "name": "parent",
                    "children": [
                        {"name": "child"},
                    ],
                },
            ]
        }
    )

    element = h(Counters, state)

    assert SpecialCounter.lifecycle == []

    gui.render(element, container)

    counter_a = container["children"][0]["children"][0]
    counter_b = container["children"][0]["children"][0]["children"][0]
    assert counter_a["type"] == "counter"
    assert counter_b["type"] == "counter"
    assert counter_a["attrs"]["count"] == 0
    assert counter_b["attrs"]["count"] == 0

    assert SpecialCounter.lifecycle == [
        "parent:before_mount",
        "child:before_mount",
        "child:mounted",
        "parent:mounted",
    ]

    # Reset lifecycle
    SpecialCounter.lifecycle = []

    for i in range(1, 6):
        # Update state by triggering all listeners, which should trigger a re-render
        for listener in counter_a["handlers"]["bump"]:
            listener()

        assert counter_a["attrs"]["count"] == i

    assert (
        SpecialCounter.lifecycle
        == [
            "parent:before_update",
            "parent:updated",
        ]
        * 5
    )

    # Reset lifecycle
    SpecialCounter.lifecycle = []

    state["counters"] = []

    assert len(container["children"][0]["children"]) == 0

    assert SpecialCounter.lifecycle == [
        "parent:before_unmount",
        "child:before_unmount",
        "child:unmounted",
        "parent:unmounted",
    ]
