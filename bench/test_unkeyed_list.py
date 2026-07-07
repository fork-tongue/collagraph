"""
Benchmarks for unkeyed v-for reconciliation (index-based), for comparison
against the keyed reconciliation path in test_keyed_list.py.

Each round replaces the whole `items` list in one reactive assignment,
see test_keyed_list.py for why (avoids per-mutation reconciliation cost
from dominating the measurement).
"""

import gc
import random

import pytest
from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer

SIZES = [10, 100, 1_000]
SIZE_IDS = ["10", "100", "1k"]
PATTERNS = ["append", "prepend", "reverse", "shuffle"]


def _new_items(items, pattern):
    if pattern == "append":
        return [*items, {"text": "x"}]
    if pattern == "prepend":
        return [{"text": "x"}, *items]
    if pattern == "reverse":
        return list(reversed(items))
    if pattern == "shuffle":
        shuffled = list(items)
        random.Random(0).shuffle(shuffled)
        return shuffled
    raise ValueError(pattern)


def _apply(gui, state, items):
    # `gui` is unused but must be kept as a live argument: it holds the
    # only strong reference to the mounted fragment tree, so passing it
    # through keeps that tree alive for the duration of the timed call.
    # GC is disabled during the timed call so that collection pauses
    # (triggered by the allocation burst) don't dominate the variance.
    gc.disable()
    try:
        state["items"] = items
    finally:
        gc.enable()


@pytest.mark.timeout(timeout=0)
@pytest.mark.benchmark(group="unkeyed_list_reconcile")
@pytest.mark.parametrize("n", SIZES, ids=SIZE_IDS)
@pytest.mark.parametrize("pattern", PATTERNS)
def test_unkeyed_list_reconcile(benchmark, parse_source, pattern, n):
    App, _ = parse_source(
        """
        <node v-for="item in items" :text="item['text']" />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    def setup():
        initial = [{"text": str(i)} for i in range(n)]
        state = reactive({"items": list(initial)})
        gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.SYNC)
        gui.render(App, {"type": "root"}, state=state)
        new_items = _new_items(initial, pattern)
        return (gui, state, new_items), {}

    benchmark.pedantic(_apply, setup=setup, warmup_rounds=1, rounds=30)
