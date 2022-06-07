from observ import reactive
import pytest

from collagraph import Collagraph, Component, create_element as h, EventLoopType
from collagraph.renderers import DictRenderer


def test_basic_dict_renderer():
    gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.SYNC)
    element = h("app")
    container = {"type": "root"}
    gui.render(element, container)

    assert container["children"][0] == {"type": "app"}


def test_renderer_required():
    with pytest.raises(TypeError):
        Collagraph(event_loop_type=EventLoopType.SYNC)


def test_lots_of_elements():
    """Render a node with a 1000 children.

    When using a recursive strategy to process fibers, this will result in a
    stack of 1000 calls to `commit_work` which triggers a RecursionError.
    This test makes sure that `collagraph` will not trigger any RecursionError.
    """
    gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    element = h("app", {}, *[h("node")] * 1000)

    gui.render(element, container)

    assert len(container["children"][0]["children"]) == 1000


def test_reactive_element():
    gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"count": 0})
    element = h("counter", state)

    gui.render(element, container)

    counter = container["children"][0]
    assert counter["type"] == "counter"
    assert counter["attrs"]["count"] == 0

    # Update state, which should trigger a re-render
    state["count"] += 1

    assert counter["attrs"]["count"] == 1, counter


def test_reactive_element_with_events(process_events):
    def Counter(props):
        def bump():
            props["count"] += 1

        return h("counter", {}, h("count", {"count": props["count"], "on_bump": bump}))

    gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.DEFAULT)
    container = {"type": "root"}
    state = reactive({"count": 0})
    element = h(Counter, state)

    gui.render(element, container)
    process_events()

    counter = container["children"][0]
    assert counter["type"] == "counter"
    counter_child = counter["children"][0]
    assert counter_child["attrs"]["count"] == 0
    assert len(counter_child["handlers"]["bump"]) == 1

    # Update state by triggering all listeners, which should trigger a re-render
    for listener in counter_child["handlers"]["bump"]:
        listener()

    process_events()

    assert counter_child["attrs"]["count"] == 1


def test_delete_item_with_children_and_siblings(process_events):
    def Item(props):
        return h(
            "item",
            None,
            *[h("part", {"title": part}) for part in props["parts"]],
        )

    def Collection(props):
        return h(
            "collection",
            None,
            *[h(Item, part) for part in props["items"]],
        )

    gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.DEFAULT)
    container = {"type": "root"}
    state = reactive(
        {
            "items": [
                {"parts": ["a"]},
                {"parts": ["b", "c"]},
                {"parts": ["d"]},
            ]
        }
    )
    element = h(Collection, state)

    gui.render(element, container)

    process_events()

    collection = container["children"][0]
    assert len(collection["children"]) == 3
    assert len(collection["children"][1]["children"]) == 2
    assert collection["children"][1]["children"][1]["type"] == "part"
    assert collection["children"][1]["children"][1]["attrs"]["title"] == "c"

    # Trigger a deletion *and* a change to the sibling for instance
    state["items"].pop(1)
    state["items"][1]["parts"][0] = "e"

    process_events()

    # TODO: check that there was only one dom update cycle needed for
    # the batched changes

    assert len(collection["children"]) == 2
    assert collection["children"][1]["children"][0]["type"] == "part"
    assert collection["children"][1]["children"][0]["attrs"]["title"] == "e"


def test_deep_reactive_element():
    def Counter(props):
        return h(
            "counter",
            None,
            h("count", props),
        )

    gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"counter": {"count": 0}})
    element = h(Counter, state)

    gui.render(element, container)

    counter = container["children"][0]
    assert counter["type"] == "counter"
    counter_child = counter["children"][0]
    assert counter_child["attrs"]["counter"]["count"] == 0

    # Update state, which should trigger a re-render
    state["counter"]["count"] += 1

    assert counter_child["attrs"]["counter"]["count"] == 1


def test_remove_attribute():
    def Foo(props):
        return h(
            "counter",
            props,
        )

    gui = Collagraph(renderer=DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"foo": True})
    element = h("foo", state)

    gui.render(element, container)

    foo = container["children"][0]
    assert foo["type"] == "foo"
    assert foo["attrs"]["foo"]

    # Update state, which should trigger a re-render
    del state["foo"]

    assert len(foo["attrs"]) == 0


def test_render_callback(process_events):
    callback_counter = 0

    def bump():
        nonlocal callback_counter
        callback_counter += 1

    gui = Collagraph(DictRenderer())
    element = h("app")
    container = {"type": "root"}
    gui.render(element, container, callback=bump)

    process_events()

    assert callback_counter == 1


def test_update_element_with_event(process_events):
    def Counter(props):
        def bump():
            props["count"] += 1

        return h("counter", {**props, "on_bump": bump})

    gui = Collagraph(DictRenderer())
    container = {"type": "root"}
    state = reactive({"count": 0})
    gui.render(h(Counter, state), container)
    process_events()

    assert container["children"][0]["attrs"]["count"] == 0
    # There should be one event listener installed
    assert len(container["children"][0]["handlers"]) == 1
    assert len(container["children"][0]["handlers"]["bump"]) == 1
    handler = container["children"][0]["handlers"]["bump"]

    state["count"] = 3
    process_events()

    assert container["children"][0]["attrs"]["count"] == 3
    # There should still be one event listener installed
    assert len(container["children"][0]["handlers"]) == 1
    assert len(container["children"][0]["handlers"]["bump"]) == 1
    # And it should be the same handler as before
    assert handler is container["children"][0]["handlers"]["bump"]


def test_yield_if_time_is_up_for_lots_of_work(process_events):
    """
    Render a node with a 1000 children in non-sync mode.
    This is probably too much work to process within the deadline
    so we can test whether the _next_unit_of_work is scheduled.
    """
    gui = Collagraph(DictRenderer())
    container = {"type": "root"}

    element = h("app", {}, *[h("node")] * 1000)
    gui.render(element, container)

    while gui._wip_root is not None:
        process_events()

    assert len(container["children"][0]["children"]) == 1000


def test_add_remove_event_handlers(process_events):
    def Counter(props):
        def reset():
            props["count"] = 0

        counter_props = {"count": props["count"]}
        if props["count"] > 0:
            # Add reset handler
            counter_props["on_reset"] = reset

        return h("counter", counter_props)

    gui = Collagraph(DictRenderer())
    container = {"type": "root"}
    state = reactive({"count": 0})
    gui.render(h(Counter, state), container)

    process_events()

    assert container["children"][0]["attrs"]["count"] == 0

    state["count"] = 1
    process_events()

    assert container["children"][0]["attrs"]["count"] == 1
    assert len(container["children"][0]["handlers"]["reset"]) == 1

    # Update state by triggering all listeners, which should trigger a re-render
    for listener in container["children"][0]["handlers"]["reset"]:
        listener()

    process_events()

    assert "on_reset" not in state
    assert len(container["children"][0]["handlers"]["reset"]) == 0


def test_change_event_handler(process_events):
    def Tick(props):
        def tick():
            props["value"] = "Tick"
            props["on_toggle"] = tock

        def tock():
            props["value"] = "Tock"
            props["on_toggle"] = tick

        own_props = {
            "on_toggle": tock,
            "value": "...",
            **props,
        }
        return h("counter", own_props)

    gui = Collagraph(DictRenderer())
    container = {"type": "root"}
    state = reactive({"count": 0})
    gui.render(h(Tick, state), container)

    process_events()

    assert container["children"][0]["attrs"]["value"] == "..."
    assert len(container["children"][0]["handlers"]["toggle"]) == 1

    # Update state by triggering all listeners, which should trigger a re-render
    for listener in container["children"][0]["handlers"]["toggle"]:
        listener()

    process_events()

    assert container["children"][0]["attrs"]["value"] == "Tock"
    assert len(container["children"][0]["handlers"]["toggle"]) == 1

    # Update state by triggering all listeners, which should trigger a re-render
    for listener in container["children"][0]["handlers"]["toggle"]:
        listener()

    process_events()

    assert container["children"][0]["attrs"]["value"] == "Tick"
    assert len(container["children"][0]["handlers"]["toggle"]) == 1


def test_only_render_on_relevant_change():
    rendered = 0

    def Foo(props):
        nonlocal rendered
        rendered += 1
        return h("foo", {"foo": props["foo"]})

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"foo": "foo", "bar": "bar"})
    gui.render(h(Foo, state), container)

    assert rendered == 1

    state["foo"] = "foe"

    assert rendered == 2

    state["bar"] = "baz"

    assert rendered == 2

    state["foo"] = "foo"

    assert rendered == 3


def test_only_render_on_relevant_change_component():
    rendered = 0

    class Foo(Component):
        def render(self):
            nonlocal rendered
            rendered += 1
            return h("foo", {"foo": self.props["foo"]})

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"foo": "foo", "bar": "bar"})
    gui.render(h(Foo, state), container)

    assert rendered == 1

    state["foo"] = "foe"

    assert rendered == 2

    state["bar"] = "baz"

    assert rendered == 2

    state["foo"] = "foo"

    assert rendered == 3
