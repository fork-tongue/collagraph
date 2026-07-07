"""
Benchmarks for updating a single reactive prop on a leaf element nested at
varying depth.

Every attribute update on a mounted fragment calls
Fragment._component_parent() to find the owning component's `updated()`
hook, which walks the parent chain. This stresses that walk relative to
tree depth.
"""

import pytest
from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer

DEPTHS = [10, 50, 200]


@pytest.mark.timeout(timeout=0)
@pytest.mark.benchmark(group="update_at_depth")
@pytest.mark.parametrize("depth", DEPTHS, ids=[str(d) for d in DEPTHS])
def test_update_attribute_at_depth(benchmark, parse_source, depth):
    open_tags = "<div>" * depth
    close_tags = "</div>" * depth
    App, _ = parse_source(
        f"""
        {open_tags}<leaf :value="value" />{close_tags}

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )
    state = reactive({"value": 0})
    gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.SYNC)
    gui.render(App, {"type": "root"}, state=state)

    counter = {"i": 0}

    def update():
        counter["i"] += 1
        state["value"] = counter["i"]

    benchmark(update)
