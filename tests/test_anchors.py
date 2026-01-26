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
