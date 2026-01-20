"""
Test that v-if does not unnecessarily remount when condition result stays the same.
"""

from observ import reactive

import collagraph as cg


def test_v_if_no_unnecessary_remount_when_condition_stays_true(
    parse_source, process_events
):
    """
    When a v-if condition depends on reactive state that changes, but the
    truthiness of the condition remains the same, the component should NOT
    be remounted.

    For example, if the condition is `count > 0`:
    - count=1 -> True, component mounts, init called
    - count=2 -> still True, component should NOT remount (init should NOT
      be called again)
    """
    # First, define a Child component with lifecycle tracking
    Child, namespace = parse_source(
        """
        <child :value="value" />

        <script>
        import collagraph as cg

        class Child(cg.Component):
            init_count = 0
            mounted_count = 0
            updated_count = 0
            before_unmount_count = 0

            def init(self):
                Child.init_count += 1

            def mounted(self):
                Child.mounted_count += 1

            def updated(self):
                Child.updated_count += 1

            def before_unmount(self):
                Child.before_unmount_count += 1
        </script>
        """
    )

    # Now define a Parent component that renders Child with v-if
    Parent, _ = parse_source(
        """
        <parent>
          <Child v-if="count > 0" :value="count" />
        </parent>

        <script>
        import collagraph as cg

        try:
            import Child
        except ImportError:
            pass

        class Parent(cg.Component):
            pass
        </script>
        """,
        namespace=namespace,
    )

    # Reset class-level counters
    Child.init_count = 0
    Child.mounted_count = 0
    Child.updated_count = 0
    Child.before_unmount_count = 0

    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.DEFAULT)
    container = {"type": "root"}
    state = reactive({"count": 1})
    gui.render(Parent, container, state=state)
    process_events()

    # Component should be mounted since count > 0
    parent = container["children"][0]
    assert parent["type"] == "parent"
    assert len(parent["children"]) == 1
    assert parent["children"][0]["type"] == "child"
    assert parent["children"][0]["attrs"]["value"] == 1

    # init and mounted should have been called exactly once
    assert Child.init_count == 1, "init should be called once on initial mount"
    assert Child.mounted_count == 1, "mounted should be called once on initial mount"
    assert Child.updated_count == 0, "updated should not be called on initial mount"
    assert Child.before_unmount_count == 0, "before_unmount should not be called yet"

    # Change count from 1 to 2 - condition is still True (2 > 0)
    state["count"] = 2
    process_events()

    # Component should still be there with updated value
    assert len(parent["children"]) == 1
    assert parent["children"][0]["attrs"]["value"] == 2

    # This is the key assertion: init should NOT be called again!
    # The condition `count > 0` is still True, so no remount should happen.
    assert Child.init_count == 1, (
        "init should still be 1 - component should not be remounted when "
        "condition stays truthy"
    )
    assert Child.mounted_count == 1, (
        "mounted should still be 1 - component should not be remounted"
    )
    # updated should be called because the :value prop changed
    assert Child.updated_count == 1, "updated should be called when props change"
    assert Child.before_unmount_count == 0, (
        "before_unmount should not be called - component was not unmounted"
    )

    # Now actually toggle the condition: count=0 means condition is False
    state["count"] = 0
    process_events()

    # Component should be unmounted
    assert "children" not in parent or len(parent["children"]) == 0

    assert Child.before_unmount_count == 1, (
        "before_unmount should be called when condition becomes false"
    )

    # Mount again
    state["count"] = 5
    process_events()

    assert len(parent["children"]) == 1
    assert parent["children"][0]["attrs"]["value"] == 5

    # Now init and mounted should have been called a second time (actual remount)
    assert Child.init_count == 2, "init should be called again after real remount"
    assert Child.mounted_count == 2, "mounted should be called again after real remount"


def test_v_if_no_unnecessary_remount_with_unchanged_truthy_value(
    parse_source, process_events
):
    """
    Test that changing a condition value to another truthy value that
    evaluates the same way does not cause a remount.
    """
    Child, namespace = parse_source(
        """
        <child />

        <script>
        import collagraph as cg

        class Child(cg.Component):
            init_count = 0
            mounted_count = 0

            def init(self):
                Child.init_count += 1

            def mounted(self):
                Child.mounted_count += 1
        </script>
        """
    )

    Parent, _ = parse_source(
        """
        <parent>
          <Child v-if="show" />
        </parent>

        <script>
        import collagraph as cg

        try:
            import Child
        except ImportError:
            pass

        class Parent(cg.Component):
            pass
        </script>
        """,
        namespace=namespace,
    )

    Child.init_count = 0
    Child.mounted_count = 0

    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.DEFAULT)
    container = {"type": "root"}
    state = reactive({"show": True})
    gui.render(Parent, container, state=state)
    process_events()

    parent = container["children"][0]
    assert len(parent["children"]) == 1
    assert Child.init_count == 1
    assert Child.mounted_count == 1

    # Change show to 1 (different truthy value, but still truthy)
    state["show"] = 1
    process_events()

    # The condition result is the same (truthy), so no remount should happen
    assert Child.init_count == 1, (
        "init should not be called when condition stays truthy"
    )
    assert Child.mounted_count == 1, (
        "mounted should not be called when condition stays truthy"
    )

    # Change to another truthy value
    state["show"] = "yes"
    process_events()

    assert Child.init_count == 1
    assert Child.mounted_count == 1
