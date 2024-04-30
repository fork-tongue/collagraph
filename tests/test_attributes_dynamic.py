from copy import deepcopy

from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer


def test_dynamic_attribute_object_method(parse_source):
    App, _ = parse_source(
        """
        <app v-bind:foo="bar()" />

        <script>
        import collagraph

        class App(collagraph.Component):
            def bar(self):
                return "baz"
        </script>
        """
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container)

    app = container["children"][0]
    assert app["attrs"]["foo"] == "baz"


def test_dynamic_attribute_object_property(parse_source):
    App, _ = parse_source(
        """
        <app :foo="bar" />

        <script>
        import collagraph

        class App(collagraph.Component):
            def __init__(self, props):
                super().__init__(props)
                self.bar = "baz"
        </script>
        """
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container)

    app = container["children"][0]
    assert app["attrs"]["foo"] == "baz"


def test_dynamic_attribute_module_scope(parse_source):
    App, _ = parse_source(
        """
        <app :foo="bar" />

        <script>
        import collagraph

        bar = "baz"

        class App(collagraph.Component):
            pass
        </script>
        """
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container)

    app = container["children"][0]
    assert app["attrs"]["foo"] == "baz"


def test_dynamic_attribute_state(parse_source):
    App, _ = parse_source(
        """
        <app :foo="bar" />

        <script>
        import collagraph

        class App(collagraph.Component):
            def __init__(self, props):
                super().__init__(props)
                self.state["bar"] = "baz"
        </script>
        """
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container)

    app = container["children"][0]
    assert app["attrs"]["foo"] == "baz"


def test_dynamic_attribute_props(parse_source):
    App, _ = parse_source(
        """
        <app :foo="bar" />

        <script>
        import collagraph

        class App(collagraph.Component):
            pass
        </script>
        """
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state={"bar": "baz"})

    app = container["children"][0]
    assert app["attrs"]["foo"] == "baz"


def test_dynamic_attribute_props_change(parse_source):
    App, _ = parse_source(
        """
        <app :foo="bar" />

        <script>
        import collagraph

        class App(collagraph.Component):
            pass
        </script>
        """
    )

    state = reactive({"bar": "baz"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    app = container["children"][0]
    assert app["attrs"]["foo"] == "baz"

    state["bar"] = "bam"

    assert app["attrs"]["foo"] == "bam"


def test_dynamic_attribute_dict(parse_source):
    App, _ = parse_source(
        """
        <app v-bind="values" />

        <script>
        import collagraph

        class App(collagraph.Component):
            pass
        </script>
        """
    )

    state = reactive({"values": {"foo": "foo"}})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    app = container["children"][0]
    assert app["attrs"]["foo"] == "foo", app

    # Change initial attribute
    state["values"]["foo"] = "bar"

    assert app["attrs"]["foo"] == "bar"

    # Add additional attribute
    state["values"]["bar"] = "bar"

    assert app["attrs"]["foo"] == "bar"
    assert app["attrs"]["bar"] == "bar"

    # Change the added attribute
    state["values"]["bar"] = "baz"

    assert app["attrs"]["bar"] == "baz"

    # Delete the initial attribute
    del state["values"]["foo"]

    assert "foo" not in app["attrs"]


def test_dynamic_attribute_deep(parse_source):
    App, _ = parse_source(
        """
        <app :values="values" />

        <script>
        import collagraph

        class App(collagraph.Component):
            pass
        </script>
        """
    )

    state = reactive({"values": {"foo": "foo"}})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    app = container["children"][0]
    assert app["attrs"]["values"] == {"foo": "foo"}, app

    # Now override the value for 'values' with a deepcopy of the original value
    app["attrs"]["values"] = deepcopy(app["attrs"]["values"])

    # Change initial attribute
    state["values"]["foo"] = "bar"

    assert app["attrs"]["values"] == {"foo": "bar"}
