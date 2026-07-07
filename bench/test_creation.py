"""
Benchmarks for the cost of mounting a fragment tree from scratch.

Mounting stresses Fragment.create()/mount(), and for elements with a
dynamic bind, also the watcher-setup path (`_watch_bind`) which relies
on the `weak()` decorator for every callback registration.
"""

import pytest
from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer

SIZES = [10, 100, 1_000]
SIZE_IDS = ["10", "100", "1k"]


@pytest.mark.timeout(timeout=0)
@pytest.mark.benchmark(group="mount_plain_elements")
@pytest.mark.parametrize("n", SIZES, ids=SIZE_IDS)
def test_mount_plain_elements(benchmark, parse_source, n):
    children = "\n".join("        <item />" for _ in range(n))
    App, _ = parse_source(
        f"""
        <root>
{children}
        </root>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    def mount():
        gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.SYNC)
        gui.render(App, {"type": "root"})

    benchmark(mount)


@pytest.mark.timeout(timeout=0)
@pytest.mark.benchmark(group="mount_bound_elements")
@pytest.mark.parametrize("n", SIZES, ids=SIZE_IDS)
def test_mount_bound_elements(benchmark, parse_source, n):
    children = "\n".join(f'        <item :value="v{i}" />' for i in range(n))
    App, _ = parse_source(
        f"""
        <root>
{children}
        </root>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )
    state = reactive({f"v{i}": i for i in range(n)})

    def mount():
        gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.SYNC)
        gui.render(App, {"type": "root"}, state=state)

    benchmark(mount)
