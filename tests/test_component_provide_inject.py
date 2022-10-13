from collagraph import Collagraph, Component, DictRenderer, EventLoopType, h


def test_component_provide_inject():
    class Child(Component):
        injected_value = None
        injected_non_existing = None
        injected_default = None

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            Child.injected_value = self.inject("value")
            Child.injected_non_existing = self.inject("non_existing")
            Child.injected_default = self.inject("other", default="bar")

        def render(self):
            return h("child")

    class Parent(Component):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.provide(key="value", value="foo")

        def render(self):
            return h("parent", {}, h(Child))

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    element = h(Parent)

    gui.render(element, container)

    assert Child.injected_value == "foo"
    assert Child.injected_non_existing is None
    assert Child.injected_default == "bar"
