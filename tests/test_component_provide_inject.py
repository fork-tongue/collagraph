import pytest

from collagraph import Collagraph, Component, DictRenderer, EventLoopType, h


def test_component_provide_inject():
    class Child(Component):
        injected_value = None
        injected_other = None
        injected_non_existing = None
        injected_default = None

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.inject("value", "other", "non_existing", default="baz")

            Child.injected_value = self.value
            Child.injected_other = self.other
            Child.injected_non_existing = self.non_existing
            Child.injected_default = self.default

        def render(self):
            return h("child")

    class Parent(Component):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # You can provide values as kwargs
            self.provide(value="foo")
            # or as a dictionary
            self.provide({"other": "bar"})

        def render(self):
            return h("parent", {}, h(Child))

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    element = h(Parent)

    gui.render(element, container)

    assert Child.injected_value == "foo"
    assert Child.injected_other == "bar"
    assert Child.injected_non_existing is None
    assert Child.injected_default == "baz"


def test_component_existing_attribute():
    class OverwriteExistingAttribute(Component):
        def mounted(self):
            # Try to inject a value that is already an attribute
            # on the component
            self.inject("parent")

        def render(self):
            return h("child")

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}

    with pytest.raises(AssertionError):
        gui.render(h(OverwriteExistingAttribute), container)

    class DoubleInjectionConflict(Component):
        def mounted(self):
            # Supply a kwarg with the same key as one of the
            # values of the args coming before
            self.inject("value", value="foo")

        def render(self):
            return h("child")

    with pytest.raises(AssertionError):
        gui.render(h(DoubleInjectionConflict), container)
