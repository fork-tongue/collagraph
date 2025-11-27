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


def test_dynamic_component_with_vif_child(parse_source):
    """Test that v-if children work correctly inside dynamic components"""
    App, _ = parse_source(
        """
        <component :is="tag">
          <child v-if="show" />
          <fallback v-else />
        </component>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"tag": "div", "show": True})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    # Initial: div with v-if showing child
    assert container["children"][0]["type"] == "div"
    assert len(container["children"][0]["children"]) == 1
    assert container["children"][0]["children"][0]["type"] == "child"

    # Toggle v-if while keeping tag same
    state["show"] = False
    assert container["children"][0]["type"] == "div"
    assert len(container["children"][0]["children"]) == 1
    assert container["children"][0]["children"][0]["type"] == "fallback"

    # Change tag while v-if is False
    state["tag"] = "span"
    assert container["children"][0]["type"] == "span"
    assert len(container["children"][0]["children"]) == 1
    assert container["children"][0]["children"][0]["type"] == "fallback"

    # Toggle v-if back while tag is span
    state["show"] = True
    assert container["children"][0]["type"] == "span"
    assert len(container["children"][0]["children"]) == 1
    assert container["children"][0]["children"][0]["type"] == "child"

    # Change tag while v-if is True
    state["tag"] = "section"
    assert container["children"][0]["type"] == "section"
    assert len(container["children"][0]["children"]) == 1
    assert container["children"][0]["children"][0]["type"] == "child"


def test_dynamic_component_with_vfor_child(parse_source):
    """Test that v-for children work correctly inside dynamic components"""
    App, _ = parse_source(
        """
        <component :is="tag">
          <item v-for="item in items" :name="item" />
        </component>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"tag": "div", "items": ["a", "b", "c"]})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    # Initial: div with v-for items
    assert container["children"][0]["type"] == "div"
    assert len(container["children"][0]["children"]) == 3
    assert container["children"][0]["children"][0]["attrs"]["name"] == "a"
    assert container["children"][0]["children"][1]["attrs"]["name"] == "b"
    assert container["children"][0]["children"][2]["attrs"]["name"] == "c"

    # Modify items while keeping tag same
    state["items"] = ["x", "y"]
    assert container["children"][0]["type"] == "div"
    assert len(container["children"][0]["children"]) == 2
    assert container["children"][0]["children"][0]["attrs"]["name"] == "x"
    assert container["children"][0]["children"][1]["attrs"]["name"] == "y"

    # Change tag while items are present
    state["tag"] = "span"
    assert container["children"][0]["type"] == "span"
    assert len(container["children"][0]["children"]) == 2
    assert container["children"][0]["children"][0]["attrs"]["name"] == "x"
    assert container["children"][0]["children"][1]["attrs"]["name"] == "y"

    # Modify items again after tag change
    state["items"] = ["p", "q", "r", "s"]
    assert container["children"][0]["type"] == "span"
    assert len(container["children"][0]["children"]) == 4
    assert container["children"][0]["children"][0]["attrs"]["name"] == "p"
    assert container["children"][0]["children"][1]["attrs"]["name"] == "q"
    assert container["children"][0]["children"][2]["attrs"]["name"] == "r"
    assert container["children"][0]["children"][3]["attrs"]["name"] == "s"

    # Change tag again with different item count
    state["tag"] = "article"
    assert container["children"][0]["type"] == "article"
    assert len(container["children"][0]["children"]) == 4


def test_dynamic_component_with_mixed_children(parse_source):
    """Test dynamic component with mix of static, v-if, and v-for children"""
    App, _ = parse_source(
        """
        <component :is="tag">
          <before />
          <conditional v-if="show" />
          <item v-for="item in items" :label="item" />
          <after />
        </component>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"tag": "div", "show": True, "items": ["1", "2"]})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    # Initial: before, conditional, item*2, after = 5 elements
    root = container["children"][0]
    assert root["type"] == "div"
    assert len(root["children"]) == 5, format_dict(container)
    assert root["children"][0]["type"] == "before"
    assert root["children"][1]["type"] == "conditional"
    assert root["children"][2]["type"] == "item"
    assert root["children"][2]["attrs"]["label"] == "1"
    assert root["children"][3]["type"] == "item"
    assert root["children"][3]["attrs"]["label"] == "2"
    assert root["children"][4]["type"] == "after"

    # Hide conditional
    state["show"] = False
    root = container["children"][0]
    assert len(root["children"]) == 4, format_dict(container)
    assert root["children"][0]["type"] == "before"
    assert root["children"][1]["type"] == "item"
    assert root["children"][2]["type"] == "item"
    assert root["children"][3]["type"] == "after"

    # Change tag while conditional is hidden
    state["tag"] = "span"
    root = container["children"][0]
    assert root["type"] == "span"
    assert len(root["children"]) == 4

    # Show conditional again
    state["show"] = True
    root = container["children"][0]
    assert len(root["children"]) == 5
    assert root["children"][0]["type"] == "before"
    assert root["children"][1]["type"] == "conditional"
    assert root["children"][2]["type"] == "item"
    assert root["children"][3]["type"] == "item"
    assert root["children"][4]["type"] == "after"

    # Modify items
    state["items"] = ["a", "b", "c"]
    root = container["children"][0]
    assert len(root["children"]) == 6  # before, conditional, item*3, after
    assert root["children"][2]["attrs"]["label"] == "a"
    assert root["children"][3]["attrs"]["label"] == "b"
    assert root["children"][4]["attrs"]["label"] == "c"

    # Change tag with all children active
    state["tag"] = "section"
    root = container["children"][0]
    assert root["type"] == "section"
    assert len(root["children"]) == 6


def test_dynamic_component_nested_control_flow(parse_source):
    """Test dynamic component with nested v-if inside v-for"""
    App, _ = parse_source(
        """
        <component :is="tag">
          <group v-for="group in groups">
            <title :text="group['name']" />
            <item v-if="group['visible']" />
          </group>
        </component>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive(
        {
            "tag": "div",
            "groups": [
                {"name": "Group1", "visible": True},
                {"name": "Group2", "visible": False},
            ],
        }
    )
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    # Initial render
    root = container["children"][0]
    assert root["type"] == "div"
    assert len(root["children"]) == 2

    # First group has title + item (visible=True)
    group1 = root["children"][0]
    assert group1["type"] == "group"
    assert len(group1["children"]) == 2
    assert group1["children"][0]["type"] == "title"
    assert group1["children"][1]["type"] == "item"

    # Second group has only title (visible=False)
    group2 = root["children"][1]
    assert group2["type"] == "group"
    assert len(group2["children"]) == 1
    assert group2["children"][0]["type"] == "title"

    # Toggle visibility
    state["groups"][1]["visible"] = True
    group2 = root["children"][1]
    assert len(group2["children"]) == 2

    # Change tag
    state["tag"] = "section"
    root = container["children"][0]
    assert root["type"] == "section"
    assert len(root["children"]) == 2

    # Verify nested structure survived tag change
    group1 = root["children"][0]
    assert len(group1["children"]) == 2
    group2 = root["children"][1]
    assert len(group2["children"]) == 2

    # Modify groups
    state["groups"] = [{"name": "GroupX", "visible": False}]
    root = container["children"][0]
    assert len(root["children"]) == 1
    assert root["children"][0]["children"][0]["attrs"]["text"] == "GroupX"
    assert len(root["children"][0]["children"]) == 1  # Only title, no item


def test_dynamic_component_nested_dynamic(parse_source):
    """Test dynamic component with nested dynamic component as child"""
    App, _ = parse_source(
        """
        <component :is="outer">
          <before />
          <component :is="inner" />
          <after />
        </component>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"outer": "div", "inner": "span"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    # Initial: outer=div, inner=span
    root = container["children"][0]
    assert root["type"] == "div"
    assert len(root["children"]) == 3
    assert root["children"][0]["type"] == "before"
    assert root["children"][1]["type"] == "span"
    assert root["children"][2]["type"] == "after"

    # Change inner tag
    state["inner"] = "article"
    root = container["children"][0]
    assert root["type"] == "div"
    assert len(root["children"]) == 3
    assert root["children"][0]["type"] == "before"
    assert root["children"][1]["type"] == "article"
    assert root["children"][2]["type"] == "after"

    # Change outer tag
    state["outer"] = "section"
    root = container["children"][0]
    assert root["type"] == "section"
    assert len(root["children"]) == 3
    assert root["children"][0]["type"] == "before"
    assert root["children"][1]["type"] == "article"
    assert root["children"][2]["type"] == "after"

    # Change both tags
    state["outer"] = "main"
    state["inner"] = "aside"
    root = container["children"][0]
    assert root["type"] == "main"
    assert len(root["children"]) == 3
    assert root["children"][0]["type"] == "before"
    assert root["children"][1]["type"] == "aside"
    assert root["children"][2]["type"] == "after"

    # Verify no old elements accumulated
    child_types = [child["type"] for child in root["children"]]
    assert child_types == ["before", "aside", "after"]
    assert "div" not in child_types
    assert "span" not in child_types
    assert "article" not in child_types
    assert "section" not in child_types


def test_dynamic_component_deeply_nested_dynamic(parse_source):
    """Test deeply nested dynamic components with children at each level"""
    App, _ = parse_source(
        """
        <component :is="level1">
          <l1-before />
          <component :is="level2">
            <l2-before />
            <component :is="level3">
              <l3-content />
            </component>
            <l2-after />
          </component>
          <l1-after />
        </component>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"level1": "div", "level2": "section", "level3": "article"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    # Initial render
    level1 = container["children"][0]
    assert level1["type"] == "div"
    assert len(level1["children"]) == 3
    assert level1["children"][0]["type"] == "l1-before"
    assert level1["children"][2]["type"] == "l1-after"

    level2 = level1["children"][1]
    assert level2["type"] == "section"
    assert len(level2["children"]) == 3
    assert level2["children"][0]["type"] == "l2-before"
    assert level2["children"][2]["type"] == "l2-after"

    level3 = level2["children"][1]
    assert level3["type"] == "article"
    assert len(level3["children"]) == 1
    assert level3["children"][0]["type"] == "l3-content"

    # Change deepest level
    state["level3"] = "aside"
    level1 = container["children"][0]
    level2 = level1["children"][1]
    level3 = level2["children"][1]
    assert level3["type"] == "aside"
    assert len(level3["children"]) == 1
    assert level3["children"][0]["type"] == "l3-content"

    # Change middle level
    state["level2"] = "nav"
    level1 = container["children"][0]
    level2 = level1["children"][1]
    assert level2["type"] == "nav"
    assert len(level2["children"]) == 3
    level3 = level2["children"][1]
    assert level3["type"] == "aside"
    assert len(level3["children"]) == 1

    # Change top level
    state["level1"] = "main"
    level1 = container["children"][0]
    assert level1["type"] == "main"
    assert len(level1["children"]) == 3
    level2 = level1["children"][1]
    assert level2["type"] == "nav"
    level3 = level2["children"][1]
    assert level3["type"] == "aside"

    # Change all levels at once
    state["level1"] = "header"
    state["level2"] = "footer"
    state["level3"] = "span"
    level1 = container["children"][0]
    assert level1["type"] == "header"
    level2 = level1["children"][1]
    assert level2["type"] == "footer"
    level3 = level2["children"][1]
    assert level3["type"] == "span"
    assert level3["children"][0]["type"] == "l3-content"

    # Verify no old elements accumulated at any level
    assert len(level1["children"]) == 3
    assert len(level2["children"]) == 3
    assert len(level3["children"]) == 1


def test_dynamic_component_with_slot(parse_source):
    """Test dynamic component switching to Component class with slot"""
    Wrapper, _ = parse_source(
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

    App, _ = parse_source(
        """
        <component :is="tag">
          <content :text="text" />
        </component>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive({"tag": "div", "text": "Hello"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    # Initial: regular div element with content as child
    root = container["children"][0]
    assert root["type"] == "div"
    assert len(root["children"]) == 1
    assert root["children"][0]["type"] == "content"
    assert root["children"][0]["attrs"]["text"] == "Hello"

    # Change to Component class with slot
    state["tag"] = Wrapper
    root = container["children"][0]
    assert root["type"] == "wrapper"
    assert len(root["children"]) == 1, format_dict(container)
    assert root["children"][0]["type"] == "content"
    assert root["children"][0]["attrs"]["text"] == "Hello"

    # Verify reactivity still works
    state["text"] = "World"
    assert root["children"][0]["attrs"]["text"] == "World"

    # Change back to regular element
    state["tag"] = "section"
    root = container["children"][0]
    assert root["type"] == "section"
    assert len(root["children"]) == 1
    assert root["children"][0]["type"] == "content"
    assert root["children"][0]["attrs"]["text"] == "World"

    # Change to different Component
    state["tag"] = Wrapper
    root = container["children"][0]
    assert root["type"] == "wrapper"
    assert len(root["children"]) == 1
    assert root["children"][0]["type"] == "content"


def test_dynamic_component_with_named_slots(parse_source):
    """Test dynamic component with Component class that has named slots"""
    Layout, _ = parse_source(
        """
        <layout>
          <header>
            <slot name="header" />
          </header>
          <main>
            <slot />
          </main>
          <footer>
            <slot name="footer" />
          </footer>
        </layout>
        <script>
        from collagraph import Component
        class Layout(Component):
            pass
        </script>
        """
    )

    App, _ = parse_source(
        """
        <component :is="tag">
          <h1 v-slot:header :title="header_text" />
          <content :text="content_text" />
          <span v-slot:footer :label="footer_text" />
        </component>
        <script>
        from collagraph import Component
        class App(Component):
            pass
        </script>
        """
    )

    state = reactive(
        {
            "tag": "div",
            "header_text": "Header",
            "content_text": "Content",
            "footer_text": "Footer",
        }
    )
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    # Initial: regular div with all children
    root = container["children"][0]
    assert root["type"] == "div"
    assert len(root["children"]) == 3
    assert root["children"][0]["type"] == "h1"
    assert root["children"][0]["attrs"]["title"] == "Header"
    assert root["children"][1]["type"] == "content"
    assert root["children"][1]["attrs"]["text"] == "Content"
    assert root["children"][2]["type"] == "span"
    assert root["children"][2]["attrs"]["label"] == "Footer"

    # Change to Layout component with named slots
    state["tag"] = Layout
    root = container["children"][0]
    assert root["type"] == "layout"

    # Check that children are properly distributed to named slots
    layout_children = root["children"]
    assert len(layout_children) == 3, format_dict(container)

    # Header slot
    header = layout_children[0]
    assert header["type"] == "header"
    assert len(header["children"]) == 1
    assert header["children"][0]["type"] == "h1"
    assert header["children"][0]["attrs"]["title"] == "Header"

    # Main slot (default)
    main = layout_children[1]
    assert main["type"] == "main"
    assert len(main["children"]) == 1
    assert main["children"][0]["type"] == "content"
    assert main["children"][0]["attrs"]["text"] == "Content"

    # Footer slot
    footer = layout_children[2]
    assert footer["type"] == "footer"
    assert len(footer["children"]) == 1
    assert footer["children"][0]["type"] == "span"
    assert footer["children"][0]["attrs"]["label"] == "Footer"

    # Verify reactivity still works
    state["header_text"] = "New Header"
    state["content_text"] = "New Content"
    state["footer_text"] = "New Footer"

    assert header["children"][0]["attrs"]["title"] == "New Header"
    assert main["children"][0]["attrs"]["text"] == "New Content"
    assert footer["children"][0]["attrs"]["label"] == "New Footer"

    # Change back to regular element
    state["tag"] = "section"
    root = container["children"][0]
    assert root["type"] == "section"
    assert len(root["children"]) == 3
    # Order should be preserved
    assert root["children"][0]["type"] == "h1"
    assert root["children"][1]["type"] == "content"
    assert root["children"][2]["type"] == "span"

    # Change back to Layout
    state["tag"] = Layout
    root = container["children"][0]
    assert root["type"] == "layout"

    # Verify slots are still correct
    layout_children = root["children"]
    assert len(layout_children[0]["children"]) == 1
    assert layout_children[0]["children"][0]["type"] == "h1"
    assert len(layout_children[1]["children"]) == 1
    assert layout_children[1]["children"][0]["type"] == "content"
    assert len(layout_children[2]["children"]) == 1
    assert layout_children[2]["children"][0]["type"] == "span"
