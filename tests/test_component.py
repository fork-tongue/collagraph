from observ import reactive

from collagraph import Collagraph, Component, create_element as h, EventLoopType


class Counter(Component):
    count = 0

    def __init__(self, props):
        super().__init__(props)
        self.count = props.get("count", 0)

    def bump(self):
        self.count += 1

    def render(self):
        # TODO: instaed of having to do: onBummp: self.bump, do something like:
        #       def on_bump
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
