import collagraph as cg


def test_components_events():
    counter = 0
    parent = None
    child = None

    class Parent(cg.Component):
        def __init__(self, props):
            super().__init__(props)
            nonlocal parent
            parent = self

        def bump(self):
            nonlocal counter
            counter += 1

        def bump_with_arg(self, step):
            nonlocal counter
            counter += step

        def render(self):
            return cg.h(
                "parent",
                {
                    "on_bump": self.bump,
                    "on_bump_step": self.bump_with_arg,
                },
                cg.h(Child),
            )

    class Child(cg.Component):
        def __init__(self, props):
            super().__init__(props)
            nonlocal child
            child = self

        def simple_event(self):
            self.emit("bump")

        def event_with_arg(self):
            self.emit("bump_step", 4)

        def render(self):
            return cg.h(
                "child",
                {
                    "on_simple_event": self.simple_event,
                    "on_event_with_arg": self.event_with_arg,
                },
            )

    gui = cg.Collagraph(event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    gui.render(cg.h(Parent), container)

    assert parent._parent is None
    assert child._parent is parent

    parent_dom = container["children"][0]
    child_dom = parent_dom["children"][0]

    assert parent_dom["type"] == "parent"
    assert child_dom["type"] == "child"
    assert counter == 0
    assert "simple_event" in child_dom["handlers"]

    for handler in child_dom["handlers"]["simple_event"]:
        handler()

    assert counter == 1

    for handler in child_dom["handlers"]["event_with_arg"]:
        handler()

    assert counter == 5
