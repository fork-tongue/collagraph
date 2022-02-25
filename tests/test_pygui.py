from observ import reactive

import pygui


def test_basic_dict_renderer():
    renderer = pygui.renderers.DictRenderer()
    gui = pygui.PyGui(renderer=renderer, sync=True)

    element = pygui.create_element("app")

    container = {"type": "root"}

    gui.render(element, container)

    assert container["children"][0] == {"type": "app"}


def test_lots_of_elements():
    """Render a node with a 1000 children.

    When using a recursive strategy to process fibers, this will result in a
    stack of 1000 calls to `commit_work` which triggers a RecursionError.
    This test makes sure that `pygui` will not trigger any RecursionError.
    """
    renderer = pygui.renderers.DictRenderer()
    gui = pygui.PyGui(renderer=renderer, sync=True)
    container = {"type": "root"}

    element = pygui.create_element("app", {}, *[pygui.create_element("node")] * 1000)
    gui.render(element, container)

    assert len(container["children"][0]["children"]) == 1000


def test_reactive_element():
    renderer = pygui.renderers.DictRenderer()
    gui = pygui.PyGui(renderer=renderer, sync=True)
    container = {"type": "root"}
    state = reactive({"counter": 0})
    element = pygui.create_element("counter", state)

    gui.render(element, container)

    counter = container["children"][0]
    assert counter["type"] == "counter"
    assert counter["counter"] == 0

    # Update state, which should trigger a re-render
    state["counter"] += 1

    counter = container["children"][0]
    assert counter["type"] == "counter"
    assert counter["counter"] == 1, counter
