from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer
from collagraph.renderers.dict_renderer import format_dict


def test_slots_dynamic_if_template():
    from tests.data.slots.dynamic_if_template import Tree

    state = reactive({"show_content": False})

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "container"}
    gui.render(Tree, container, state)

    root = container["children"][0]
    assert root["type"] == "node"
    assert "children" not in root

    state["show_content"] = True

    assert "children" in root, format_dict(root)
    assert len(root["children"]) == 1, format_dict(root)

    state["show_content"] = False

    assert "children" not in root, format_dict


def test_slots_dynamic_for_template():
    from tests.data.slots.dynamic_for_template import Tree

    state = reactive({"content": ["a", "b"]})

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "container"}
    gui.render(Tree, container, state)

    root = container["children"][0]
    assert root["type"] == "node"
    assert "children" in root
    assert len(root["children"]) == 2

    state["content"].append("c")

    assert len(root["children"]) == 3, format_dict(root)

    state["content"].remove("a")

    assert len(root["children"]) == 2, format_dict(root)

    state["content"] = []

    assert "children" not in root, format_dict(root)


def test_slots_dynamic_if():
    from tests.data.slots.dynamic_if import Tree

    state = reactive({"show_content": False})

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "container"}
    gui.render(Tree, container, state)

    root = container["children"][0]
    assert root["type"] == "node"
    assert "children" not in root

    state["show_content"] = True

    assert "children" in root, format_dict(root)
    assert len(root["children"]) == 1, format_dict(root)

    state["show_content"] = False

    assert "children" not in root, format_dict


def test_slots_dynamic_for():
    from tests.data.slots.dynamic_for import Tree

    state = reactive({"content": ["a", "b"]})

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "container"}
    gui.render(Tree, container, state)

    root = container["children"][0]
    assert root["type"] == "node"
    assert "children" in root
    assert len(root["children"]) == 2

    state["content"].append("c")

    assert len(root["children"]) == 3, format_dict(root)

    state["content"].remove("a")

    assert len(root["children"]) == 2, format_dict(root)

    state["content"] = []

    assert "children" not in root, format_dict(root)


def test_slots_dynamic_component():
    from tests.data.slots.dynamic_component import Tree

    state = reactive({"component_type": "foo", "value": "initial"})

    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "container"}
    gui.render(Tree, container, state)

    root = container["children"][0]
    assert root["type"] == "node"
    assert "children" in root, format_dict(root)
    assert len(root["children"]) == 1
    assert root["children"][0]["type"] == "foo", format_dict(root)
    assert root["children"][0]["attrs"]["value"] == "initial", format_dict(root)

    # Change the dynamic component type
    state["component_type"] = "bar"

    assert len(root["children"]) == 1, format_dict(root)
    assert root["children"][0]["type"] == "bar", format_dict(root)
    assert root["children"][0]["attrs"]["value"] == "initial", format_dict(root)

    # Change the bound attribute
    state["value"] = "updated"

    assert root["children"][0]["attrs"]["value"] == "updated", format_dict(root)


def test_slots_lowercase_component_alias_with_vif(parse_source):
    """
    Test that v-if works in slots when the parent component is imported
    with a lowercase alias. This would fail if component detection only
    checked for uppercase first letter.
    """

    # Use lowercase alias 'node' for the Node component with v-if in slot
    # The 'node' alias is imported in the script, so it's in the 'names' set
    App, _ = parse_source(
        """
        <node>
          <content v-if="show" />
        </node>

        <script>
        from collagraph import Component
        from tests.data.slots.node import Node as node

        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"show": False})
    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "container"}
    gui.render(App, container, state)

    root = container["children"][0]
    assert root["type"] == "node"
    assert "children" not in root, format_dict(root)

    # Toggle v-if condition
    state["show"] = True

    assert "children" in root, format_dict(root)
    assert len(root["children"]) == 1
    assert root["children"][0]["type"] == "content"

    state["show"] = False

    assert "children" not in root, format_dict(root)


def test_slots_lowercase_component_alias_with_vfor(parse_source):
    """
    Test that v-for works in slots when the parent component is imported
    with a lowercase alias. This would fail if component detection only
    checked for uppercase first letter.
    """

    # Use lowercase alias 'node' for the Node component with v-for in slot
    # The 'node' alias is imported in the script, so it's in the 'names' set
    App, _ = parse_source(
        """
        <node>
          <item v-for="x in items" :value="x" />
        </node>

        <script>
        from collagraph import Component
        from tests.data.slots.node import Node as node

        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"items": ["a", "b"]})
    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "container"}
    gui.render(App, container, state)

    root = container["children"][0]
    assert root["type"] == "node"
    assert "children" in root, format_dict(root)
    assert len(root["children"]) == 2

    # Add item
    state["items"].append("c")
    assert len(root["children"]) == 3, format_dict(root)

    # Remove items
    state["items"] = []
    assert "children" not in root, format_dict(root)


def test_slots_dotted_component_with_vif(parse_source):
    """
    Test that v-if works in slots when the parent component uses
    dot notation (e.g., module.Component). This would fail if component
    detection only checked for uppercase first letter.
    """
    # Create a simple module-like namespace with a component
    wrapper, _ = parse_source(
        """
        <wrapper>
          <slot />
        </wrapper>

        <script>
        from collagraph import Component

        class Wrapper(Component):
            pass
        </script>
        """
    )

    # Create a simple class to act as a module namespace
    class components:  # noqa: N801
        pass

    components.wrap = wrapper

    # Use dot notation for the component
    App, _ = parse_source(
        """
        <components.wrap>
          <content v-if="show" />
        </components.wrap>

        <script>
        from collagraph import Component

        class App(Component):
            pass
        </script>
        """,
        namespace={"components": components},
    )

    state = reactive({"show": False})
    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "container"}
    gui.render(App, container, state)

    root = container["children"][0]
    assert root["type"] == "wrapper"
    assert "children" not in root, format_dict(root)

    # Toggle v-if condition
    state["show"] = True

    assert "children" in root, format_dict(root)
    assert len(root["children"]) == 1
    assert root["children"][0]["type"] == "content"
