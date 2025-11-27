from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer
from collagraph.renderers.dict_renderer import format_dict


def test_dynamic_component_tag(parse_source):
    App, _ = parse_source(
        """
        <component :is="foo" />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"foo": "foo"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == 1
    assert container["children"][0]["type"] == "foo"

    state["foo"] = "bar"

    assert len(container["children"]) == 1
    assert container["children"][0]["type"] == "bar"


def test_dynamic_component_tag_anchor(parse_source):
    App, _ = parse_source(
        """
        <first />
        <component :is="foo" />
        <last />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"foo": "foo"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == 3
    assert container["children"][0]["type"] == "first", format_dict(container)
    assert container["children"][1]["type"] == "foo", format_dict(container)
    assert container["children"][2]["type"] == "last", format_dict(container)

    state["foo"] = "bar"

    assert len(container["children"]) == 3
    assert container["children"][0]["type"] == "first", format_dict(container)
    assert container["children"][1]["type"] == "bar", format_dict(container)
    assert container["children"][2]["type"] == "last", format_dict(container)


def test_dynamic_component_tag_component(parse_source):
    A, _ = parse_source(
        """
        <a :name="name" />
        <script>
        from collagraph import Component
        class A(Component):
            pass
        </script>
        """
    )
    B, _ = parse_source(
        """
        <b :name="name" />
        <script>
        from collagraph import Component
        class B(Component):
            pass
        </script>
        """
    )
    App, _ = parse_source(
        """
        <component :is="element_type" :name="name" />
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"name": "foo", "element_type": A})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["attrs"]["name"] == "foo"
    assert container["children"][0]["type"] == "a"

    state["element_type"] = B

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["attrs"]["name"] == "foo"
    assert container["children"][0]["type"] == "b"

    # Check that reactivity still works
    state["name"] = "bar"

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["type"] == "b"
    assert container["children"][0]["attrs"]["name"] == "bar"

    state["element_type"] = A

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["type"] == "a"
    assert container["children"][0]["attrs"]["name"] == "bar"


def test_dynamic_component_tag_component_and_element(parse_source):
    A, _ = parse_source(
        """
        <a :name="name" />
        <script>
        from collagraph import Component
        class A(Component):
            pass
        </script>
        """
    )
    App, _ = parse_source(
        """
        <component :is="element_type" :name="name" />
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"name": "foo", "element_type": A})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["attrs"]["name"] == "foo"
    assert container["children"][0]["type"] == "a"

    state["element_type"] = "b"

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["attrs"]["name"] == "foo"
    assert container["children"][0]["type"] == "b"

    # Check that reactivity still works
    state["name"] = "bar"

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["type"] == "b"
    assert container["children"][0]["attrs"]["name"] == "bar"

    state["element_type"] = A

    assert len(container["children"]) == 1, container["children"]
    assert container["children"][0]["attrs"]["name"] == "bar"
    assert container["children"][0]["type"] == "a"


def test_dynamic_component_with_vfor(parse_source):
    App, _ = parse_source(
        """
        <div>
          <component v-for="tag in tags" :is="tag" :name="tag" />
        </div>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"tags": ["foo", "bar", "baz"]})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    div = container["children"][0]
    assert len(div["children"]) == 3, format_dict(container)
    assert div["children"][0]["type"] == "foo"
    assert div["children"][0]["attrs"]["name"] == "foo"
    assert div["children"][1]["type"] == "bar"
    assert div["children"][1]["attrs"]["name"] == "bar"
    assert div["children"][2]["type"] == "baz"
    assert div["children"][2]["attrs"]["name"] == "baz"

    # Modify the list
    state["tags"] = ["qux", "bar"]

    assert len(div["children"]) == 2, format_dict(container)
    assert div["children"][0]["type"] == "qux"
    assert div["children"][0]["attrs"]["name"] == "qux"
    assert div["children"][1]["type"] == "bar"
    assert div["children"][1]["attrs"]["name"] == "bar"


def test_dynamic_component_with_vfor_components(parse_source):
    """Test dynamic component with Component classes inside v-for"""
    A, _ = parse_source(
        """
        <a :label="label" />
        <script>
        from collagraph import Component
        class A(Component):
            pass
        </script>
        """
    )
    B, _ = parse_source(
        """
        <b :label="label" />
        <script>
        from collagraph import Component
        class B(Component):
            pass
        </script>
        """
    )
    App, _ = parse_source(
        """
        <div>
          <component
            v-for="item in items"
            :is="item['type']"
            :label="item['label']"
          />
        </div>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive(
        {
            "items": [
                {"type": A, "label": "First"},
                {"type": B, "label": "Second"},
                {"type": A, "label": "Third"},
            ]
        }
    )
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    div = container["children"][0]
    assert len(div["children"]) == 3, format_dict(container)
    assert div["children"][0]["type"] == "a"
    assert div["children"][0]["attrs"]["label"] == "First"
    assert div["children"][1]["type"] == "b"
    assert div["children"][1]["attrs"]["label"] == "Second"
    assert div["children"][2]["type"] == "a"
    assert div["children"][2]["attrs"]["label"] == "Third"

    # Update the list
    state["items"][1]["type"] = A
    state["items"][1]["label"] = "Changed"

    assert len(div["children"]) == 3, format_dict(container)
    assert div["children"][1]["type"] == "a"
    assert div["children"][1]["attrs"]["label"] == "Changed"


def test_dynamic_component_with_vif(parse_source):
    """Test dynamic component with v-if"""
    App, _ = parse_source(
        """
        <div>
          <component v-if="show" :is="tag" :name="name" />
          <fallback v-else />
        </div>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"show": True, "tag": "foo", "name": "test"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    div = container["children"][0]
    assert len(div["children"]) == 1, format_dict(container)
    assert div["children"][0]["type"] == "foo"
    assert div["children"][0]["attrs"]["name"] == "test"

    # Toggle to hide
    state["show"] = False

    assert len(div["children"]) == 1, format_dict(container)
    assert div["children"][0]["type"] == "fallback"

    # Toggle back and change tag
    state["show"] = True
    state["tag"] = "bar"

    assert len(div["children"]) == 1, format_dict(container)
    assert div["children"][0]["type"] == "bar"
    assert div["children"][0]["attrs"]["name"] == "test"


def test_dynamic_component_nested_vfor(parse_source):
    """Test dynamic component with nested v-for loops"""
    App, _ = parse_source(
        """
        <div>
          <group v-for="group in groups" :name="group['name']">
            <component
              v-for="item in group['items']"
              :is="item"
            />
          </group>
        </div>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive(
        {
            "groups": [
                {"name": "Group1", "items": ["a", "b"]},
                {"name": "Group2", "items": ["c", "d", "e"]},
            ]
        }
    )
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    div = container["children"][0]
    assert len(div["children"]) == 2, format_dict(container)

    # First group
    group1 = div["children"][0]
    assert group1["type"] == "group"
    assert group1["attrs"]["name"] == "Group1"
    assert len(group1["children"]) == 2
    assert group1["children"][0]["type"] == "a"
    assert group1["children"][1]["type"] == "b"

    # Second group
    group2 = div["children"][1]
    assert group2["type"] == "group"
    assert group2["attrs"]["name"] == "Group2"
    assert len(group2["children"]) == 3
    assert group2["children"][0]["type"] == "c"
    assert group2["children"][1]["type"] == "d"
    assert group2["children"][2]["type"] == "e"

    # Modify nested items
    state["groups"][0]["items"] = ["x", "y", "z"]

    group1 = div["children"][0]
    assert len(group1["children"]) == 3, format_dict(container)
    assert group1["children"][0]["type"] == "x"
    assert group1["children"][1]["type"] == "y"
    assert group1["children"][2]["type"] == "z"


def test_dynamic_component_old_elements_removed(parse_source):
    """
    Regression test: Ensure old active_fragment elements don't accumulate
    when DynamicFragment changes tags.

    Bug: When changing from tag 'div' to 'span', the old 'div' element
    was being added as a child of the new 'span' element because
    active fragments were incorrectly registered in DynamicFragment.children
    and then transferred to the new active fragment.
    """
    App, _ = parse_source(
        """
        <component :is="tag">
          <child />
        </component>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"tag": "div"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    # Initial render: div with one child
    assert len(container["children"]) == 1
    assert container["children"][0]["type"] == "div"
    assert "children" in container["children"][0], format_dict(container)
    assert len(container["children"][0]["children"]) == 1
    assert container["children"][0]["children"][0]["type"] == "child"

    # Change to span - old div should be removed, not become a child
    state["tag"] = "span"

    assert len(container["children"]) == 1, format_dict(container)
    assert container["children"][0]["type"] == "span"
    assert "children" in container["children"][0], format_dict(container)
    assert len(container["children"][0]["children"]) == 1, format_dict(container)
    assert container["children"][0]["children"][0]["type"] == "child"
    # Bug would cause: children = ["child", "div"] - old div becomes a child!

    # Multiple changes should not accumulate old elements
    state["tag"] = "section"
    assert len(container["children"][0]["children"]) == 1, format_dict(container)
    assert container["children"][0]["children"][0]["type"] == "child"

    state["tag"] = "article"
    assert len(container["children"][0]["children"]) == 1, format_dict(container)
    assert container["children"][0]["children"][0]["type"] == "child"

    # Verify no old elements (span, section) accumulated
    child_types = [child["type"] for child in container["children"][0]["children"]]
    assert child_types == ["child"], f"Expected ['child'], got {child_types}"
    assert "span" not in child_types
    assert "section" not in child_types
    assert "div" not in child_types
