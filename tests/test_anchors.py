"""Tests for anchor logic ensuring correct element ordering with v-if directives."""

from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer


def test_anchor_ordering_with_nested_components(parse_source):
    """
    Test that elements are correctly ordered when v-if toggles inside nested components.
    """
    _Simple, namespace = parse_source(
        """
        <item
          v-if="value"
          :name="name"
        />
        <script>
        import collagraph as cg
        class Simple(cg.Component):
            pass
        </script>
        """
    )

    Parent, namespace = parse_source(
        """
        <parent>
          <Simple :value="first" name="first" />
          <Simple :value="second" name="second" />
          <Simple :value="third" name="third" />
        </parent>
        <script>
        import collagraph as cg
        try:
            from simple import Simple
        except ImportError:
            pass
        class Parent(cg.Component):
            pass
        </script>
        """,
        namespace,
    )

    state = reactive(
        {
            "first": True,
            "second": True,
            "third": True,
        }
    )

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(Parent, container, state=state)

    def get_child_names():
        parent = container["children"][0]
        return [child["attrs"]["name"] for child in parent.get("children", [])]

    # Initial state: all three visible
    assert get_child_names() == ["first", "second", "third"]

    # Hide second
    state["second"] = False
    assert get_child_names() == ["first", "third"]

    # Show second again - should be in correct position
    state["second"] = True
    assert get_child_names() == ["first", "second", "third"]


def test_anchor_ordering_hide_first(parse_source):
    """Test hiding and showing the first element."""
    _Simple, namespace = parse_source(
        """
        <item
          v-if="value"
          :name="name"
        />
        <script>
        import collagraph as cg
        class Simple(cg.Component):
            pass
        </script>
        """
    )

    Parent, namespace = parse_source(
        """
        <parent>
          <Simple :value="first" name="first" />
          <Simple :value="second" name="second" />
          <Simple :value="third" name="third" />
        </parent>
        <script>
        import collagraph as cg
        try:
            from simple import Simple
        except ImportError:
            pass
        class Parent(cg.Component):
            pass
        </script>
        """,
        namespace,
    )

    state = reactive(
        {
            "first": True,
            "second": True,
            "third": True,
        }
    )

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(Parent, container, state=state)

    def get_child_names():
        parent = container["children"][0]
        return [child["attrs"]["name"] for child in parent.get("children", [])]

    assert get_child_names() == ["first", "second", "third"]

    # Hide first
    state["first"] = False
    assert get_child_names() == ["second", "third"]

    # Show first again
    state["first"] = True
    assert get_child_names() == ["first", "second", "third"]


def test_anchor_ordering_hide_last(parse_source):
    """Test hiding and showing the last element."""
    _Simple, namespace = parse_source(
        """
        <item
          v-if="value"
          :name="name"
        />
        <script>
        import collagraph as cg
        class Simple(cg.Component):
            pass
        </script>
        """
    )

    Parent, namespace = parse_source(
        """
        <parent>
          <Simple :value="first" name="first" />
          <Simple :value="second" name="second" />
          <Simple :value="third" name="third" />
        </parent>
        <script>
        import collagraph as cg
        try:
            from simple import Simple
        except ImportError:
            pass
        class Parent(cg.Component):
            pass
        </script>
        """,
        namespace,
    )

    state = reactive(
        {
            "first": True,
            "second": True,
            "third": True,
        }
    )

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(Parent, container, state=state)

    def get_child_names():
        parent = container["children"][0]
        return [child["attrs"]["name"] for child in parent.get("children", [])]

    assert get_child_names() == ["first", "second", "third"]

    # Hide last
    state["third"] = False
    assert get_child_names() == ["first", "second"]

    # Show last again
    state["third"] = True
    assert get_child_names() == ["first", "second", "third"]


def test_anchor_ordering_hide_multiple(parse_source):
    """Test hiding and showing multiple elements."""
    _Simple, namespace = parse_source(
        """
        <item
          v-if="value"
          :name="name"
        />
        <script>
        import collagraph as cg
        class Simple(cg.Component):
            pass
        </script>
        """
    )

    Parent, namespace = parse_source(
        """
        <parent>
          <Simple :value="first" name="first" />
          <Simple :value="second" name="second" />
          <Simple :value="third" name="third" />
        </parent>
        <script>
        import collagraph as cg
        try:
            from simple import Simple
        except ImportError:
            pass
        class Parent(cg.Component):
            pass
        </script>
        """,
        namespace,
    )

    state = reactive(
        {
            "first": True,
            "second": True,
            "third": True,
        }
    )

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(Parent, container, state=state)

    def get_child_names():
        parent = container["children"][0]
        return [child["attrs"]["name"] for child in parent.get("children", [])]

    assert get_child_names() == ["first", "second", "third"]

    # Hide first and third
    state["first"] = False
    state["third"] = False
    assert get_child_names() == ["second"]

    # Show them back in reverse order
    state["third"] = True
    assert get_child_names() == ["second", "third"]

    state["first"] = True
    assert get_child_names() == ["first", "second", "third"]


def test_anchor_ordering_v_if_without_component_wrapper(parse_source):
    """Test v-if ordering without nested component wrappers."""
    App, _ = parse_source(
        """
        <parent>
          <item v-if="first" name="first" />
          <item v-if="second" name="second" />
          <item v-if="third" name="third" />
        </parent>
        <script>
        import collagraph as cg
        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive(
        {
            "first": True,
            "second": True,
            "third": True,
        }
    )

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(App, container, state=state)

    def get_child_names():
        parent = container["children"][0]
        return [child["attrs"]["name"] for child in parent.get("children", [])]

    assert get_child_names() == ["first", "second", "third"]

    # Hide second
    state["second"] = False
    assert get_child_names() == ["first", "third"]

    # Show second again
    state["second"] = True
    assert get_child_names() == ["first", "second", "third"]


def test_anchor_ordering_template_with_v_if(parse_source):
    """
    Test that children of virtual fragments (template) are positioned correctly.

    When a <template> element (which has no DOM element itself) contains children
    and is toggled with v-if, the children must be inserted at the correct position
    using the anchor. This tests that Fragment.mount() passes the anchor to children
    when the fragment has no element.
    """
    App, _ = parse_source(
        """
        <parent>
          <item name="first" />
          <template v-if="show_middle">
            <item name="second" />
            <item name="third" />
          </template>
          <item name="fourth" />
        </parent>
        <script>
        import collagraph as cg
        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"show_middle": True})

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(App, container, state=state)

    def get_child_names():
        parent = container["children"][0]
        return [child["attrs"]["name"] for child in parent.get("children", [])]

    # Initial state: all visible
    assert get_child_names() == ["first", "second", "third", "fourth"]

    # Hide the template children
    state["show_middle"] = False
    assert get_child_names() == ["first", "fourth"]

    # Show template children again - they should appear between first and fourth
    state["show_middle"] = True
    assert get_child_names() == ["first", "second", "third", "fourth"]


def test_anchor_ordering_nested_templates_with_v_if(parse_source):
    """
    Test anchor ordering with nested virtual fragments (templates).

    This tests a more complex scenario where templates are nested and each
    level needs to correctly propagate the anchor to its children.
    """
    App, _ = parse_source(
        """
        <parent>
          <item name="a" />
          <template v-if="show_outer">
            <item name="b" />
            <template v-if="show_inner">
              <item name="c" />
              <item name="d" />
            </template>
            <item name="e" />
          </template>
          <item name="f" />
        </parent>
        <script>
        import collagraph as cg
        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"show_outer": True, "show_inner": True})

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(App, container, state=state)

    def get_child_names():
        parent = container["children"][0]
        return [child["attrs"]["name"] for child in parent.get("children", [])]

    # Initial state: all visible
    assert get_child_names() == ["a", "b", "c", "d", "e", "f"]

    # Hide inner template
    state["show_inner"] = False
    assert get_child_names() == ["a", "b", "e", "f"]

    # Show inner template again
    state["show_inner"] = True
    assert get_child_names() == ["a", "b", "c", "d", "e", "f"]

    # Hide outer template (which includes inner)
    state["show_outer"] = False
    assert get_child_names() == ["a", "f"]

    # Show outer template again
    state["show_outer"] = True
    assert get_child_names() == ["a", "b", "c", "d", "e", "f"]


def test_anchor_ordering_deeply_nested_components(parse_source):
    """Test anchor ordering with deeply nested component structure."""
    _Inner, namespace = parse_source(
        """
        <item
          v-if="value"
          :name="name"
        />
        <script>
        import collagraph as cg
        class Inner(cg.Component):
            pass
        </script>
        """
    )

    _Wrapper, namespace = parse_source(
        """
        <Inner :value="value" :name="name" />
        <script>
        import collagraph as cg
        try:
            from inner import Inner
        except ImportError:
            pass
        class Wrapper(cg.Component):
            pass
        </script>
        """,
        namespace,
    )

    Parent, namespace = parse_source(
        """
        <parent>
          <Wrapper :value="first" name="first" />
          <Wrapper :value="second" name="second" />
          <Wrapper :value="third" name="third" />
        </parent>
        <script>
        import collagraph as cg
        try:
            from wrapper import Wrapper
        except ImportError:
            pass
        class Parent(cg.Component):
            pass
        </script>
        """,
        namespace,
    )

    state = reactive(
        {
            "first": True,
            "second": True,
            "third": True,
        }
    )

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(Parent, container, state=state)

    def get_child_names():
        parent = container["children"][0]
        return [child["attrs"]["name"] for child in parent.get("children", [])]

    assert get_child_names() == ["first", "second", "third"]

    # Hide second
    state["second"] = False
    assert get_child_names() == ["first", "third"]

    # Show second again
    state["second"] = True
    assert get_child_names() == ["first", "second", "third"]


def test_anchor_issue(parse_source):
    _, namespace = parse_source(
        """
        <foo v-if="True" :name="name">
          <slot />
        </foo>

        <script>
        import collagraph as cg
        class Foo(cg.Component):
            pass
        </script>
        """
    )
    _, namespace = parse_source(
        """
        <bar v-if="True" :name="name" />

        <script>
        import collagraph as cg
        class Bar(cg.Component):
            pass
        </script>
        """,
        namespace=namespace,
    )
    _, namespace = parse_source(
        """
        <component
          v-bind="props"
          :is="type_map(obj_type)"
        >
          <Item
            v-for="item in props.get('children', [])"
            v-bind="item"
          />
        </component>


        <script>
        import collagraph as cg
        try:
            from foo import Foo
        except ImportError:
            pass
        try:
            from bar import Bar
        except ImportError:
            pass

        def type_map(obj_type):
            return {"foo": Foo, "bar": Bar}[obj_type]


        class Item(cg.Component):
            pass
        </script>
        """,
        namespace=namespace,
    )

    App, namespace = parse_source(
        """
        <Item
          v-for="it in items"
          v-bind="it"
        />

        <script>
        try:
            import Item
        except ImportError:
            pass


        import collagraph as cg
        class App(cg.Component):
            pass
        </script>
        """,
        namespace=namespace,
    )

    state = reactive({"items": []})

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(App, container, state=state)

    assert "children" not in container

    state["items"].append({"obj_type": "foo", "name": "foo-1"})

    assert len(container["children"]) == 1
    assert container["children"][0]["type"] == "foo"
    assert container["children"][0]["attrs"]["name"] == "foo-1"

    state["items"].append({"obj_type": "foo", "name": "foo-2"})

    assert len(container["children"]) == 2

    # Now add a child item to the first item.
    # This produces the following error
    # ValueError: list.index(x): x not in list
    # It is now passing the second foo item from the root as the anchor
    # which is not correct!
    state["items"][0]["children"] = [{"obj_type": "bar", "name": "bar-1"}]
