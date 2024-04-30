from observ import reactive

from collagraph import EventLoopType, Collagraph
from collagraph.renderers import DictRenderer


def test_directive_else_root(parse_source):
    App, _ = parse_source(
        """
        <foo v-if="foo" />
        <bar v-else />

        <script>
        import collagraph

        class App(collagraph.Component):
            pass
        </script>
        """
    )

    state = reactive({"foo": False})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == 1
    assert container["children"][0]["type"] == "bar"

    state["foo"] = True

    assert len(container["children"]) == 1
    assert container["children"][0]["type"] == "foo"

    state["foo"] = False

    assert len(container["children"]) == 1
    assert container["children"][0]["type"] == "bar"


def test_directive_else_surrounded(parse_source):
    App, _ = parse_source(
        """
        <before />
        <foo v-if="foo" />
        <bar v-else />
        <after />

        <script>
        import collagraph

        class App(collagraph.Component):
            pass
        </script>
        """
    )

    state = reactive({"foo": False})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == 3
    assert container["children"][0]["type"] == "before"
    assert container["children"][1]["type"] == "bar"
    assert container["children"][2]["type"] == "after"

    state["foo"] = True

    assert len(container["children"]) == 3
    assert container["children"][0]["type"] == "before"
    assert container["children"][1]["type"] == "foo"
    assert container["children"][2]["type"] == "after"

    state["foo"] = False

    assert len(container["children"]) == 3
    assert container["children"][0]["type"] == "before"
    assert container["children"][1]["type"] == "bar"
    assert container["children"][2]["type"] == "after"
