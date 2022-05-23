import collagraph as cg


class Container(cg.Component):
    def render(self):
        return cg.h(
            "container",
            {},
            cg.h("header", None, *self.render_slot("header")),
            cg.h("content", None, *self.render_slot("default")),
            cg.h("footer", None, *self.render_slot("footer")),
        )


class ContainerDefaults(cg.Component):
    def render(self):
        return cg.h(
            "container",
            {},
            cg.h("header", None, *self.s("header") or (cg.h("header-default"),)),
            cg.h("content", None, *self.s("default") or (cg.h("default"),)),
            cg.h("footer", None, *self.s("footer") or (cg.h("footer-default"),)),
        )


def test_component_named_slots_empty():
    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    element = cg.h(Container)

    gui.render(element, container)

    container = container["children"][0]
    assert container["type"] == "container"

    header, content, footer = container["children"]

    assert "children" not in content
    assert "children" not in header
    assert "children" not in footer


def test_component_named_slots_defaults():
    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    element = cg.h(ContainerDefaults)

    gui.render(element, container)

    container = container["children"][0]
    assert container["type"] == "container"

    header, content, footer = container["children"]

    assert header["children"][0]["type"] == "header-default"
    assert content["children"][0]["type"] == "default"
    assert footer["children"][0]["type"] == "footer-default"


def test_component_named_slots_filled():
    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    element = cg.h(
        Container,
        {},
        {
            "footer": lambda props: cg.h("footer-content"),
            "default": lambda props: cg.h("content"),
            "header": lambda props: cg.h("header-content"),
        },
    )

    gui.render(element, container)

    container = container["children"][0]
    assert container["type"] == "container"

    header, content, footer = container["children"]

    assert header["children"][0]["type"] == "header-content"
    assert content["children"][0]["type"] == "content"
    assert footer["children"][0]["type"] == "footer-content"


def test_component_named_slots_partial_filled():
    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    element = cg.h(
        ContainerDefaults,
        {},
        {
            # Don't provide slot content for default
            "footer": lambda props: cg.h("footer-content"),
            "header": lambda props: cg.h("header-content"),
        },
    )

    gui.render(element, container)

    container = container["children"][0]
    assert container["type"] == "container"

    header, content, footer = container["children"]

    assert header["children"][0]["type"] == "header-content"
    # Default slot should have default content
    assert content["children"][0]["type"] == "default"
    assert footer["children"][0]["type"] == "footer-content"


def test_component_default_slot():
    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    element = cg.h(
        Container,
        {},
        # Provide default slot content by providing a callable slot
        lambda props: cg.h("content"),
    )

    gui.render(element, container)

    container = container["children"][0]
    assert container["type"] == "container"

    header, content, footer = container["children"]

    assert "children" not in header
    assert content["children"][0]["type"] == "content"
    assert "children" not in footer


def test_component_multiple_items_as_slot_content():
    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    element = cg.h(
        Container,
        {},
        # Provide multiple elements as slot content
        lambda props: (cg.h("content"), cg.h("more")),
    )

    gui.render(element, container)

    container = container["children"][0]
    assert container["type"] == "container"

    header, content, footer = container["children"]

    assert "children" not in header
    assert content["children"][0]["type"] == "content"
    assert content["children"][1]["type"] == "more"
    assert "children" not in footer
