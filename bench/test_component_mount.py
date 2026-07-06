"""
Benchmarks for mounting a chain of nested components.

Each level is its own ComponentFragment, so this stresses per-component
mount overhead: the weak()-wrapped ref/bind watchers set up in
ComponentFragment.create(), and the root-element lookup at the end of
ComponentFragment.mount() (self.first()).
"""

import pytest

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer

DEPTHS = [10, 50, 200]


def _build_nested_component(parse_source, depth):
    Leaf, _ = parse_source(
        """
        <leaf />

        <script>
        import collagraph as cg

        class Leaf(cg.Component):
            pass
        </script>
        """
    )

    prev = Leaf
    prev_name = "Leaf"
    for i in range(depth):
        name = f"Wrapper{i}"
        prev, _ = parse_source(
            f"""
            <div>
              <{prev_name} />
            </div>

            <script>
            import collagraph as cg

            class {name}(cg.Component):
                pass
            </script>
            """,
            namespace={prev_name: prev},
        )
        prev_name = name

    return prev


@pytest.mark.timeout(timeout=0)
@pytest.mark.benchmark(group="mount_nested_components")
@pytest.mark.parametrize("depth", DEPTHS, ids=[str(d) for d in DEPTHS])
def test_mount_nested_components(benchmark, parse_source, depth):
    App = _build_nested_component(parse_source, depth)

    def mount():
        gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.SYNC)
        gui.render(App, {"type": "root"})

    benchmark(mount)
