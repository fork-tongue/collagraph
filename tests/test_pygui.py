from observ import reactive

from pygui import create_element as h, EventLoopType, PyGui
from pygui.renderers import DictRenderer


def test_basic_dict_renderer():
    renderer = DictRenderer()
    gui = PyGui(renderer=renderer, event_loop_type=EventLoopType.SYNC)

    element = h("app")

    container = {"type": "root"}

    gui.render(element, container)

    assert container["children"][0] == {"type": "app"}


def test_lots_of_elements():
    """Render a node with a 1000 children.

    When using a recursive strategy to process fibers, this will result in a
    stack of 1000 calls to `commit_work` which triggers a RecursionError.
    This test makes sure that `pygui` will not trigger any RecursionError.
    """
    renderer = DictRenderer()
    gui = PyGui(renderer=renderer, event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}

    element = h("app", {}, *[h("node")] * 1000)
    gui.render(element, container)

    assert len(container["children"][0]["children"]) == 1000


def test_reactive_element():
    renderer = DictRenderer()
    gui = PyGui(renderer=renderer, event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"counter": 0})
    element = h("counter", state)

    gui.render(element, container)

    counter = container["children"][0]
    assert counter["type"] == "counter"
    assert counter["counter"] == 0

    # Update state, which should trigger a re-render
    state["counter"] += 1

    counter = container["children"][0]
    assert counter["type"] == "counter"
    assert counter["counter"] == 1, counter


def test_reactive_element_with_events(process_events):
    def Counter(props):
        props.setdefault("count", 0)

        def bump():
            props["count"] += 1

        return h(
            "counter", props, h("count", {"count": props["count"], "onBump": bump})
        )

    renderer = DictRenderer()
    gui = PyGui(renderer=renderer, event_loop_type=EventLoopType.DEFAULT)
    container = {"type": "root"}
    state = reactive({"count": 0})
    element = h(Counter, state)

    gui.render(element, container)
    process_events()

    counter = container["children"][0]
    assert counter["type"] == "counter"
    assert counter["children"][0]["count"] == 0
    assert len(counter["children"][0]["event_listeners"]["bump"]) == 1

    # Update state by triggering all listeners, which should trigger a re-render
    for listener in counter["children"][0]["event_listeners"]["bump"]:
        listener()

    process_events()
    counter = container["children"][0]
    assert counter["children"][0]["count"] == 1


def test_delete_item_with_children_and_siblings(process_events):
    def Item(props):
        props.setdefault("parts", [])
        return h(
            "item",
            props,
            *[h("part", {"title": part}) for part in props["parts"]],
        )

    def Collection(props):
        props.setdefault("items", [])
        return h(
            "collection",
            props,
            *[h(Item, part) for part in props["items"]],
        )

    renderer = DictRenderer()
    gui = PyGui(renderer=renderer, event_loop_type=EventLoopType.DEFAULT)
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
    assert collection["children"][1]["children"][1]["title"] == "c"

    # Trigger a deletion *and* a change to the sibling for instance
    state["items"].pop(1)
    state["items"][1]["parts"][0] = "e"

    process_events()

    # TODO: check that there was only one dom update cycle needed for
    # the batched changes

    assert len(collection["children"]) == 2
    assert collection["children"][1]["children"][0]["type"] == "part"
    assert collection["children"][1]["children"][0]["title"] == "e"


def test_deep_reactive_element():
    def Counter(props):
        return h(
            "counter",
            props,
            h("count", props),
        )

    renderer = DictRenderer()
    gui = PyGui(renderer=renderer, event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"counter": {"count": 0}})
    element = h(Counter, state)

    gui.render(element, container)

    counter = container["children"][0]
    assert counter["type"] == "counter"
    assert counter["children"][0]["counter"]["count"] == 0

    # Update state, which should trigger a re-render
    state["counter"]["count"] += 1

    counter = container["children"][0]
    assert counter["type"] == "counter"
    assert counter["children"][0]["counter"]["count"] == 1, counter
