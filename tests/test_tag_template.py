from collagraph import EventLoopType, Collagraph
from collagraph.renderers import DictRenderer


def test_basic_dict_renderer(parse_source):
    App, _ = parse_source(
        """
        <template>
          <foo />
        </template>

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

    assert len(container["children"]) == 1
    assert container["children"][0]["type"] == "foo"

    App = None
    _ = None
    container = None
    gui = None
