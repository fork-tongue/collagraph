"""
Benchmarks for growing/shrinking an unkeyed v-for in a single reactive
assignment.

Growing by n items calls Fragment.anchor() once per appended item, even
though the anchor is loop-invariant during the update, so these
benchmarks measure that redundant tree walking. The `siblings` variant
places a static element after the v-for so that every anchor() call
also has to resolve an actual sibling element instead of returning
None.
"""

import pytest
from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer

SIZES = [100, 1_000]
SIZE_IDS = ["100", "1k"]

PLAIN_TEMPLATE = """
<node v-for="item in items" :text="item['text']" />

<script>
import collagraph as cg

class App(cg.Component):
    pass
</script>
"""

SIBLINGS_TEMPLATE = """
<template>
  <header />
  <node v-for="item in items" :text="item['text']" />
  <footer />
</template>

<script>
import collagraph as cg

class App(cg.Component):
    pass
</script>
"""


def _apply(gui, state, items):
    # `gui` is unused but must be kept as a live argument: it holds the
    # only strong reference to the mounted fragment tree, so passing it
    # through keeps that tree alive for the duration of the timed call.
    state["items"] = items


def _setup(parse_source, template, initial_items, target_items):
    App, _ = parse_source(template)

    def setup():
        state = reactive({"items": list(initial_items)})
        gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.SYNC)
        gui.render(App, {"type": "root"}, state=state)
        return (gui, state, list(target_items)), {}

    return setup


@pytest.mark.timeout(timeout=0)
@pytest.mark.benchmark(group="unkeyed_list_grow")
@pytest.mark.parametrize("n", SIZES, ids=SIZE_IDS)
def test_unkeyed_list_grow(benchmark, parse_source, n):
    items = [{"text": str(i)} for i in range(n)]
    setup = _setup(parse_source, PLAIN_TEMPLATE, [], items)
    benchmark.pedantic(_apply, setup=setup, warmup_rounds=1, rounds=20)


@pytest.mark.timeout(timeout=0)
@pytest.mark.benchmark(group="unkeyed_list_grow")
@pytest.mark.parametrize("n", SIZES, ids=SIZE_IDS)
def test_unkeyed_list_grow_with_siblings(benchmark, parse_source, n):
    items = [{"text": str(i)} for i in range(n)]
    setup = _setup(parse_source, SIBLINGS_TEMPLATE, [], items)
    benchmark.pedantic(_apply, setup=setup, warmup_rounds=1, rounds=20)


@pytest.mark.timeout(timeout=0)
@pytest.mark.benchmark(group="unkeyed_list_grow")
@pytest.mark.parametrize("n", SIZES, ids=SIZE_IDS)
def test_unkeyed_list_shrink(benchmark, parse_source, n):
    items = [{"text": str(i)} for i in range(n)]
    setup = _setup(parse_source, PLAIN_TEMPLATE, items, [])
    benchmark.pedantic(_apply, setup=setup, warmup_rounds=1, rounds=20)
