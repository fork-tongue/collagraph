from collagraph import EventLoopType, Collagraph
from collagraph.renderers import DictRenderer


def test_static_attributes(parse_source):
    App, _ = parse_source(
        """
        <app foo="bar" baz />

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
    gui.render(App, container)

    app = container["children"][0]
    assert app["attrs"]["foo"] == "bar"
    assert app["attrs"]["baz"] is True


def test_static_attributes_nested_elements(parse_source):
    App, _ = parse_source(
        """
        <app foo="bar">
          <item text="baz" />
        </app>

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
    gui.render(App, container)

    app = container["children"][0]
    assert app["attrs"]["foo"] == "bar"

    item = app["children"][0]
    assert item["attrs"]["text"] == "baz"


def test_static_bool_attribute(parse_source):
    App, _ = parse_source(
        """
        <app foo />

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
    gui.render(App, container)

    app = container["children"][0]
    assert app["attrs"]["foo"] is True
