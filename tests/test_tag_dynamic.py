from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer
from collagraph.renderers.dict_renderer import format_dict


def test_dynamic_component_tag(parse_source):
    App, _ = parse_source(
        """
        <component :is="foo" />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"foo": "foo"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == 1
    assert container["children"][0]["type"] == "foo"

    state["foo"] = "bar"

    assert len(container["children"]) == 1
    assert container["children"][0]["type"] == "bar"


def test_dynamic_component_tag_anchor(parse_source):
    App, _ = parse_source(
        """
        <first />
        <component :is="foo" />
        <last />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"foo": "foo"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == 3
    assert container["children"][0]["type"] == "first", format_dict(container)
    assert container["children"][1]["type"] == "foo", format_dict(container)
    assert container["children"][2]["type"] == "last", format_dict(container)

    state["foo"] = "bar"

    assert len(container["children"]) == 3
    assert container["children"][0]["type"] == "first", format_dict(container)
    assert container["children"][1]["type"] == "bar", format_dict(container)
    assert container["children"][2]["type"] == "last", format_dict(container)


def test_dynamic_component_tag_component(parse_source):
    A, _ = parse_source(
        """
        <a :name="name" />
        <script>
        from collagraph import Component
        class A(Component):
            pass
        </script>
        """
    )
    B, _ = parse_source(
        """
        <b :name="name" />
        <script>
        from collagraph import Component
        class B(Component):
            pass
        </script>
        """
    )
    App, _ = parse_source(
        """
        <component :is="element_type" :name="name" />
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"name": "foo", "element_type": A})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["attrs"]["name"] == "foo"
    assert container["children"][0]["type"] == "a"

    state["element_type"] = B

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["attrs"]["name"] == "foo"
    assert container["children"][0]["type"] == "b"

    # Check that reactivity still works
    state["name"] = "bar"

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["type"] == "b"
    assert container["children"][0]["attrs"]["name"] == "bar"

    state["element_type"] = A

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["type"] == "a"
    assert container["children"][0]["attrs"]["name"] == "bar"


def test_dynamic_component_tag_component_and_element(parse_source):
    A, _ = parse_source(
        """
        <a :name="name" />
        <script>
        from collagraph import Component
        class A(Component):
            pass
        </script>
        """
    )
    App, _ = parse_source(
        """
        <component :is="element_type" :name="name" />
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"name": "foo", "element_type": A})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["attrs"]["name"] == "foo"
    assert container["children"][0]["type"] == "a"

    state["element_type"] = "b"

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["attrs"]["name"] == "foo"
    assert container["children"][0]["type"] == "b"

    # Check that reactivity still works
    state["name"] = "bar"

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["type"] == "b"
    assert container["children"][0]["attrs"]["name"] == "bar"

    state["element_type"] = A

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["attrs"]["name"] == "bar"
    assert container["children"][0]["type"] == "a"
