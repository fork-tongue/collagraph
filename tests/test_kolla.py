import pytest
from observ import reactive

from collagraph import EventLoopType, Collagraph
from collagraph.renderers import DictRenderer


def test_basic_dict_renderer(parse_source):
    App, _ = parse_source(
        """
        <app/>

        <script>
        import collagraph

        class App(collagraph.Component):
            pass
        </script>
        """
    )

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(App, container)

    assert container["children"][0] == {"type": "app"}


def test_renderer_required():
    # renderer argument is required
    with pytest.raises(TypeError):
        Collagraph(event_loop_type=EventLoopType.SYNC)

    # When the renderer argument is passed, it should be a Renderer subclass
    with pytest.raises(TypeError) as e:
        Collagraph(
            renderer=True,
            event_loop_type=EventLoopType.SYNC,
        )

    assert "Expected a Renderer" in str(e)


def test_reactive_element(parse_source):
    App, _ = parse_source(
        """
        <counter
          :count="count"
        />

        <script>
        import collagraph

        class App(collagraph.Component):
            pass
        </script>
        """
    )

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    state = reactive({"count": 0})

    gui.render(App, container, state)

    counter = container["children"][0]
    assert counter["type"] == "counter"
    assert counter["attrs"]["count"] == 0

    # Update state, which should trigger a re-render
    state["count"] += 1

    assert counter["attrs"]["count"] == 1, counter
