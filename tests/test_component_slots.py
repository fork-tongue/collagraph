from observ import reactive

import collagraph as cg


def test_component_empty_slot():
    from tests.data.slots import Container

    gui = cg.Collagraph(event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({})
    # No children defined for container
    element = cg.h(Container, state)

    gui.render(element, container)

    container = container["children"][0]
    assert container["type"] == "container"

    before, after = container["children"]
    assert before["type"] == "before"
    assert after["type"] == "after"


def test_component_filled_slot():
    from tests.data.slots import Container

    gui = cg.Collagraph(event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({})
    # Add 'content' as slot content
    element = cg.h(Container, state, cg.h("content"))

    gui.render(element, container)

    container = container["children"][0]
    assert container["type"] == "container"

    before, content, after = container["children"]
    assert before["type"] == "before"
    assert after["type"] == "after"
    assert content["type"] == "content"


def test_component_default_slot_content():
    from tests.data.slots_default import Container

    gui = cg.Collagraph(event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({})
    # No children defined for container
    element = cg.h(Container, state)

    gui.render(element, container)

    container = container["children"][0]
    assert container["type"] == "container"

    before, content, after = container["children"]
    assert before["type"] == "before"
    assert after["type"] == "after"
    assert content["type"] == "default-content"


def test_component_named_slots_empty():
    from tests.data.slots_named import Container

    gui = cg.Collagraph(event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({})
    # No children defined for container
    element = cg.h(Container, state)

    gui.render(element, container)

    container = container["children"][0]
    assert container["type"] == "container"

    for item, name in zip(container["children"], ["a", "b", "c", "d"]):
        assert item["type"] == "item"
        assert item["attrs"]["name"] == name


def test_component_named_slots_filled():
    from tests.data.slots_named import Container

    gui = cg.Collagraph(event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({})
    # No children defined for container
    element = cg.h(
        Container,
        state,
        cg.h("content", {"v-slot:after": True, "name": "after"}),
        cg.h("content", {"v-slot:default": True, "name": "default"}),
        cg.h("content", {"v-slot:before": True, "name": "before"}),
    )

    gui.render(element, container)

    container = container["children"][0]
    assert container["type"] == "container"

    for item, name in zip(
        container["children"], ["a", "before", "b", "default", "c", "after", "d"]
    ):
        assert item["type"] in {"item", "content"}
        assert item["attrs"]["name"] == name
