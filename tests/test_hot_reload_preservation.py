"""Tests for hot reload preservation of props, events, static attributes, and refs.

These tests verify that component configuration is preserved across hot reload,
including:
- Static props passed to child components
- Dynamic props (bound with :prop syntax)
- Event handlers (@event syntax)
- Static attributes on elements
- Dynamic attributes on elements
- Refs (both static and dynamic)
- Slot contents

The hot reload implementation preserves _attributes, _binds, _events, _ref_name,
and _ref_is_dynamic before unmount and restores them before remount. This ensures
that static props, dynamic props, event handlers, and refs work correctly after
hot reload.
"""

import sys
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

import collagraph as cg
from collagraph.sfc.importer import _loaded_cgx_modules


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test components."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        sys.path.insert(0, str(tmpdir))
        yield tmpdir
        sys.path.remove(str(tmpdir))
        # Clean up modules
        for name in list(sys.modules.keys()):
            module = sys.modules[name]
            if hasattr(module, "__file__") and module.__file__:
                if str(tmpdir) in module.__file__:
                    del sys.modules[name]
        _loaded_cgx_modules.clear()


def write_component(path: Path, content: str) -> None:
    """Write component content to file, stripping leading whitespace."""
    path.write_text(dedent(content).lstrip())


def test_static_props_preserved_after_reload(temp_dir):
    """Static props passed to a child component should be preserved after reload."""
    # Create child component that displays its props
    child_path = temp_dir / "static_props_child.cgx"
    write_component(
        child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class StaticPropsChild(cg.Component):
            def init(self):
                name = self.props.get("name", "unknown")
                count = self.props.get("count", 0)
                self.state["display_text"] = f"{name}: {count} (v1)"
        </script>
        """,
    )

    # Create parent that passes static props
    parent_path = temp_dir / "static_props_parent.cgx"
    write_component(
        parent_path,
        """
        <StaticPropsChild name="TestItem" count="42" />

        <script>
        import collagraph as cg

        from static_props_child import StaticPropsChild


        class StaticPropsParent(cg.Component):
            pass
        </script>
        """,
    )

    import static_props_parent

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(static_props_parent.StaticPropsParent, container)

    # Verify initial render with props
    assert container["children"][0]["attrs"]["text"] == "TestItem: 42 (v1)"

    # Update the child component
    write_component(
        child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class StaticPropsChild(cg.Component):
            def init(self):
                name = self.props.get("name", "unknown")
                count = self.props.get("count", 0)
                self.state["display_text"] = f"{name}: {count} (v2)"
        </script>
        """,
    )

    # Trigger fine-grained reload
    changed_paths = {child_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # Props should still be available - the component should receive the same props
    assert container["children"][0]["attrs"]["text"] == "TestItem: 42 (v2)"


def test_dynamic_props_preserved_after_reload(temp_dir):
    """Dynamic props bound with :prop syntax should be preserved after reload."""
    # Create child component
    child_path = temp_dir / "dynamic_props_child.cgx"
    write_component(
        child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class DynamicPropsChild(cg.Component):
            def init(self):
                value = self.props.get("value", 0)
                self.state["display_text"] = f"Value: {value} (v1)"
        </script>
        """,
    )

    # Create parent that passes dynamic props
    parent_path = temp_dir / "dynamic_props_parent.cgx"
    write_component(
        parent_path,
        """
        <DynamicPropsChild :value="computed_value" />

        <script>
        import collagraph as cg

        from dynamic_props_child import DynamicPropsChild


        class DynamicPropsParent(cg.Component):
            def init(self):
                self.state["base_value"] = 100

            @property
            def computed_value(self):
                return self.state["base_value"] * 2
        </script>
        """,
    )

    import dynamic_props_parent

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(dynamic_props_parent.DynamicPropsParent, container)

    # Verify initial render - computed_value should be 100 * 2 = 200
    assert container["children"][0]["attrs"]["text"] == "Value: 200 (v1)"

    # Update the child component
    write_component(
        child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class DynamicPropsChild(cg.Component):
            def init(self):
                value = self.props.get("value", 0)
                self.state["display_text"] = f"Value: {value} (v2)"
        </script>
        """,
    )

    # Trigger fine-grained reload
    changed_paths = {child_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # Dynamic prop should still work - value should still be 200
    assert container["children"][0]["attrs"]["text"] == "Value: 200 (v2)"


def test_event_handlers_preserved_after_reload(temp_dir):
    """Event handlers (@event syntax) should work after reload."""
    # Create child component that emits an event
    child_path = temp_dir / "event_child.cgx"
    write_component(
        child_path,
        """
        <button text="Click me v1" @click="handle_click" />

        <script>
        import collagraph as cg

        class EventChild(cg.Component):
            def handle_click(self):
                self.emit("custom-event", "from-child-v1")
        </script>
        """,
    )

    # Create parent that handles the event
    parent_path = temp_dir / "event_parent.cgx"
    write_component(
        parent_path,
        """
        <widget>
            <EventChild @custom-event="on_event" />
            <label :text="received_value" />
        </widget>

        <script>
        import collagraph as cg

        from event_child import EventChild


        class EventParent(cg.Component):
            def init(self):
                self.state["received_value"] = "none"

            def on_event(self, value):
                self.state["received_value"] = value
        </script>
        """,
    )

    import event_parent

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(event_parent.EventParent, container)

    # Get reference to child component
    widget = container["children"][0]
    label = widget["children"][1]
    assert label["attrs"]["text"] == "none"

    def find_child_component(fragment):
        """Helper to find the EventChild component in the fragment tree."""
        from collagraph.fragment import ComponentFragment, ListFragment

        if isinstance(fragment, ComponentFragment) and fragment.component:
            if type(fragment.component).__name__ == "EventChild":
                return fragment

        # Check rendered_fragment for component usage sites
        if isinstance(fragment, ComponentFragment) and fragment.rendered_fragment:
            result = find_child_component(fragment.rendered_fragment)
            if result:
                return result

        # Check slot_content
        if isinstance(fragment, ComponentFragment):
            for slot_fragments in fragment.slot_content.values():
                for child in slot_fragments:
                    result = find_child_component(child)
                    if result:
                        return result

        # Check generated fragments for ListFragment
        if isinstance(fragment, ListFragment):
            for child in fragment._generated_fragments:
                result = find_child_component(child)
                if result:
                    return result

        # Check template_children
        for child in fragment.template_children:
            result = find_child_component(child)
            if result:
                return result
        return None

    # Find the child component and emit an event before reload
    child_fragment = find_child_component(gui.fragment)
    assert child_fragment is not None, "Should find EventChild component"
    child_fragment.component.emit("custom-event", "test-before-reload")
    assert label["attrs"]["text"] == "test-before-reload"

    # Update the child component
    write_component(
        child_path,
        """
        <button text="Click me v2" @click="handle_click" />

        <script>
        import collagraph as cg

        class EventChild(cg.Component):
            def handle_click(self):
                self.emit("custom-event", "from-child-v2")
        </script>
        """,
    )

    # Trigger fine-grained reload
    changed_paths = {child_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # Find the new child component and emit an event
    child_fragment = find_child_component(gui.fragment)
    assert child_fragment is not None, "Should find EventChild after reload"
    child_fragment.component.emit("custom-event", "test-after-reload")

    # Event handler should still work
    assert label["attrs"]["text"] == "test-after-reload"


def test_static_attributes_preserved_on_child_elements(temp_dir):
    """Static attributes on child elements within a component should be preserved."""
    # Create a component with nested elements that have static attributes
    comp_path = temp_dir / "static_attrs_comp.cgx"
    write_component(
        comp_path,
        """
        <widget class="container" style="padding: 10px">
            <label id="title" :text="title_text" class="header" />
        </widget>

        <script>
        import collagraph as cg

        class StaticAttrsComp(cg.Component):
            def init(self):
                self.state["title_text"] = "Title v1"
        </script>
        """,
    )

    import static_attrs_comp

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(static_attrs_comp.StaticAttrsComp, container)

    # Verify initial render with static attributes
    widget = container["children"][0]
    assert widget["attrs"]["class"] == "container"
    assert widget["attrs"]["style"] == "padding: 10px"

    label = widget["children"][0]
    assert label["attrs"]["id"] == "title"
    assert label["attrs"]["class"] == "header"
    assert label["attrs"]["text"] == "Title v1"

    # Update the component
    write_component(
        comp_path,
        """
        <widget class="container" style="padding: 10px">
            <label id="title" :text="title_text" class="header" />
        </widget>

        <script>
        import collagraph as cg

        class StaticAttrsComp(cg.Component):
            def init(self):
                self.state["title_text"] = "Title v2"
        </script>
        """,
    )

    # Do a full reload (since this is the root component)
    result = gui.reload(preserve_state=False)
    assert result is True

    # Static attributes should be preserved on child elements
    widget = container["children"][0]
    assert widget["attrs"]["class"] == "container"
    assert widget["attrs"]["style"] == "padding: 10px"

    label = widget["children"][0]
    assert label["attrs"]["id"] == "title"
    assert label["attrs"]["class"] == "header"
    assert label["attrs"]["text"] == "Title v2"


def test_dynamic_attributes_preserved_on_elements(temp_dir):
    """Dynamic attributes bound with :attr syntax should be preserved after reload."""
    # Create component with dynamic attributes
    comp_path = temp_dir / "dynamic_attrs_comp.cgx"
    write_component(
        comp_path,
        """
        <widget :class="widget_class">
            <label :text="label_text" :style="label_style" />
        </widget>

        <script>
        import collagraph as cg

        class DynamicAttrsComp(cg.Component):
            def init(self):
                self.state["widget_class"] = "my-widget"
                self.state["label_text"] = "Dynamic v1"
                self.state["label_style"] = "color: red"
        </script>
        """,
    )

    import dynamic_attrs_comp

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(dynamic_attrs_comp.DynamicAttrsComp, container)

    # Verify initial render
    widget = container["children"][0]
    assert widget["attrs"]["class"] == "my-widget"

    label = widget["children"][0]
    assert label["attrs"]["text"] == "Dynamic v1"
    assert label["attrs"]["style"] == "color: red"

    # Modify state to verify it's actually dynamic
    gui.fragment.component.state["label_style"] = "color: blue"
    assert label["attrs"]["style"] == "color: blue"

    # Update the component
    write_component(
        comp_path,
        """
        <widget :class="widget_class">
            <label :text="label_text" :style="label_style" />
        </widget>

        <script>
        import collagraph as cg

        class DynamicAttrsComp(cg.Component):
            def init(self):
                self.state["widget_class"] = "new-widget"
                self.state["label_text"] = "Dynamic v2"
                self.state["label_style"] = "color: green"
        </script>
        """,
    )

    # Reload with state preservation
    result = gui.reload(preserve_state=True)
    assert result is True

    # State should be preserved, so dynamic attributes should have old values
    widget = container["children"][0]
    assert widget["attrs"]["class"] == "my-widget"

    label = widget["children"][0]
    assert label["attrs"]["style"] == "color: blue"  # We changed this to blue


def test_static_ref_available_after_reload(temp_dir):
    """Static refs should be re-registered after hot reload."""
    # Create component with a static ref
    comp_path = temp_dir / "static_ref_comp.cgx"
    write_component(
        comp_path,
        """
        <widget>
            <label ref="my_label" :text="label_text" />
        </widget>

        <script>
        import collagraph as cg

        class StaticRefComp(cg.Component):
            def init(self):
                self.state["label_text"] = "With ref v1"

            def get_ref_type(self):
                if hasattr(self, "refs") and "my_label" in self.refs:
                    return self.refs["my_label"].get("type", "unknown")
                return None
        </script>
        """,
    )

    import static_ref_comp

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(static_ref_comp.StaticRefComp, container)

    # Verify ref is available
    component = gui.fragment.component
    assert component.get_ref_type() == "label"

    # Update the component
    write_component(
        comp_path,
        """
        <widget>
            <label ref="my_label" :text="label_text" />
        </widget>

        <script>
        import collagraph as cg

        class StaticRefComp(cg.Component):
            def init(self):
                self.state["label_text"] = "With ref v2"

            def get_ref_type(self):
                if hasattr(self, "refs") and "my_label" in self.refs:
                    return self.refs["my_label"].get("type", "unknown")
                return None
        </script>
        """,
    )

    # Reload
    result = gui.reload(preserve_state=False)
    assert result is True

    # Ref should be available on the new component
    component = gui.fragment.component
    assert component.get_ref_type() == "label"


def test_slot_content_props_preserved(temp_dir):
    """Props passed to components in slot content should be preserved."""
    # Create a simple slot child
    slot_child_path = temp_dir / "slot_content_child.cgx"
    write_component(
        slot_child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class SlotContentChild(cg.Component):
            def init(self):
                msg = self.props.get("message", "default")
                self.state["display_text"] = f"Message: {msg} (v1)"
        </script>
        """,
    )

    # Create wrapper with slot
    wrapper_path = temp_dir / "slot_content_wrapper.cgx"
    write_component(
        wrapper_path,
        """
        <widget class="wrapper">
            <slot />
        </widget>

        <script>
        import collagraph as cg

        class SlotContentWrapper(cg.Component):
            pass
        </script>
        """,
    )

    # Create parent using wrapper with slot content
    parent_path = temp_dir / "slot_content_parent.cgx"
    write_component(
        parent_path,
        """
        <SlotContentWrapper>
            <SlotContentChild message="Hello World" />
        </SlotContentWrapper>

        <script>
        import collagraph as cg

        from slot_content_wrapper import SlotContentWrapper
        from slot_content_child import SlotContentChild


        class SlotContentParent(cg.Component):
            pass
        </script>
        """,
    )

    import slot_content_parent

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(slot_content_parent.SlotContentParent, container)

    # Verify initial render
    wrapper = container["children"][0]
    assert wrapper["attrs"]["class"] == "wrapper"
    label = wrapper["children"][0]
    assert label["attrs"]["text"] == "Message: Hello World (v1)"

    # Update the slot child
    write_component(
        slot_child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class SlotContentChild(cg.Component):
            def init(self):
                msg = self.props.get("message", "default")
                self.state["display_text"] = f"Message: {msg} (v2)"
        </script>
        """,
    )

    # Trigger fine-grained reload
    changed_paths = {slot_child_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # Props should still be passed - message should still be "Hello World"
    label = wrapper["children"][0]
    assert label["attrs"]["text"] == "Message: Hello World (v2)"


def test_mixed_props_preserved(temp_dir):
    """Components receiving both static and dynamic props should preserve both."""
    # Create child component
    child_path = temp_dir / "mixed_child.cgx"
    write_component(
        child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class MixedChild(cg.Component):
            def init(self):
                static_val = self.props.get("static_prop", "missing")
                dynamic_val = self.props.get("dynamic_prop", "missing")
                self.state["display_text"] = f"S:{static_val} D:{dynamic_val} (v1)"
        </script>
        """,
    )

    # Create parent with mixed props
    parent_path = temp_dir / "mixed_parent.cgx"
    write_component(
        parent_path,
        """
        <MixedChild static_prop="static-value" :dynamic_prop="get_dynamic()" />

        <script>
        import collagraph as cg

        from mixed_child import MixedChild


        class MixedParent(cg.Component):
            def init(self):
                self.state["dynamic_value"] = "dynamic-value"

            def get_dynamic(self):
                return self.state["dynamic_value"]
        </script>
        """,
    )

    import mixed_parent

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(mixed_parent.MixedParent, container)

    # Verify initial render
    label = container["children"][0]
    assert label["attrs"]["text"] == "S:static-value D:dynamic-value (v1)"

    # Update the child component
    write_component(
        child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class MixedChild(cg.Component):
            def init(self):
                static_val = self.props.get("static_prop", "missing")
                dynamic_val = self.props.get("dynamic_prop", "missing")
                self.state["display_text"] = f"S:{static_val} D:{dynamic_val} (v2)"
        </script>
        """,
    )

    # Trigger fine-grained reload
    changed_paths = {child_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # Both static and dynamic props should be preserved
    label = container["children"][0]
    assert label["attrs"]["text"] == "S:static-value D:dynamic-value (v2)"


def test_deeply_nested_props_preserved(temp_dir):
    """Props at multiple nesting levels should all be preserved."""
    # Create leaf component
    leaf_path = temp_dir / "nested_leaf.cgx"
    write_component(
        leaf_path,
        """
        <label :text="text" />

        <script>
        import collagraph as cg

        class NestedLeaf(cg.Component):
            def init(self):
                val = self.props.get("value", "missing")
                self.state["text"] = f"Leaf: {val} (v1)"
        </script>
        """,
    )

    # Create middle component
    middle_path = temp_dir / "nested_middle.cgx"
    write_component(
        middle_path,
        """
        <widget>
            <NestedLeaf :value="middle_value" />
        </widget>

        <script>
        import collagraph as cg

        from nested_leaf import NestedLeaf


        class NestedMiddle(cg.Component):
            def init(self):
                prefix = self.props.get("prefix", "")
                self.state["middle_value"] = f"{prefix}-middle"
        </script>
        """,
    )

    # Create root component
    root_path = temp_dir / "nested_root.cgx"
    write_component(
        root_path,
        """
        <NestedMiddle prefix="root" />

        <script>
        import collagraph as cg

        from nested_middle import NestedMiddle


        class NestedRoot(cg.Component):
            pass
        </script>
        """,
    )

    import nested_root

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(nested_root.NestedRoot, container)

    # Verify initial render
    widget = container["children"][0]
    label = widget["children"][0]
    assert label["attrs"]["text"] == "Leaf: root-middle (v1)"

    # Update the leaf component
    write_component(
        leaf_path,
        """
        <label :text="text" />

        <script>
        import collagraph as cg

        class NestedLeaf(cg.Component):
            def init(self):
                val = self.props.get("value", "missing")
                self.state["text"] = f"Leaf: {val} (v2)"
        </script>
        """,
    )

    # Trigger fine-grained reload of just the leaf
    changed_paths = {leaf_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # Props should still flow through the chain
    widget = container["children"][0]
    label = widget["children"][0]
    assert label["attrs"]["text"] == "Leaf: root-middle (v2)"


def test_vfor_item_props_preserved(temp_dir):
    """Props passed to items in v-for should be preserved after reload."""
    # Create item component
    item_path = temp_dir / "vfor_item.cgx"
    write_component(
        item_path,
        """
        <label :text="item_text" />

        <script>
        import collagraph as cg

        class VforItem(cg.Component):
            def init(self):
                name = self.props.get("name", "unknown")
                self.state["item_text"] = f"{name} (v1)"
        </script>
        """,
    )

    # Create list component
    list_path = temp_dir / "vfor_list.cgx"
    write_component(
        list_path,
        """
        <widget>
            <VforItem
                v-for="item in items"
                :key="item"
                :name="item"
            />
        </widget>

        <script>
        import collagraph as cg

        from vfor_item import VforItem


        class VforList(cg.Component):
            pass
        </script>
        """,
    )

    import vfor_list

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    state = {"items": ["alpha", "beta", "gamma"]}
    gui.render(vfor_list.VforList, container, state=state)

    # Verify initial render
    widget = container["children"][0]
    assert len(widget["children"]) == 3
    assert widget["children"][0]["attrs"]["text"] == "alpha (v1)"
    assert widget["children"][1]["attrs"]["text"] == "beta (v1)"
    assert widget["children"][2]["attrs"]["text"] == "gamma (v1)"

    # Update the item component
    write_component(
        item_path,
        """
        <label :text="item_text" />

        <script>
        import collagraph as cg

        class VforItem(cg.Component):
            def init(self):
                name = self.props.get("name", "unknown")
                self.state["item_text"] = f"{name} (v2)"
        </script>
        """,
    )

    # Trigger fine-grained reload
    changed_paths = {item_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # All items should still have correct props
    widget = container["children"][0]
    assert len(widget["children"]) == 3
    assert widget["children"][0]["attrs"]["text"] == "alpha (v2)"
    assert widget["children"][1]["attrs"]["text"] == "beta (v2)"
    assert widget["children"][2]["attrs"]["text"] == "gamma (v2)"


def test_dynamic_component_props_preserved(temp_dir):
    """Props passed via :is dynamic components should be preserved."""
    # Create component to be dynamically rendered
    dynamic_path = temp_dir / "dynamic_target.cgx"
    write_component(
        dynamic_path,
        """
        <label :text="display" />

        <script>
        import collagraph as cg

        class DynamicTarget(cg.Component):
            def init(self):
                val = self.props.get("target_prop", "missing")
                self.state["display"] = f"Target: {val} (v1)"
        </script>
        """,
    )

    # Create parent using :is
    parent_path = temp_dir / "dynamic_component_parent.cgx"
    write_component(
        parent_path,
        """
        <component :is="get_comp()" target_prop="my-value" />

        <script>
        import collagraph as cg

        from dynamic_target import DynamicTarget


        def get_comp():
            return DynamicTarget


        class DynamicComponentParent(cg.Component):
            pass
        </script>
        """,
    )

    import dynamic_component_parent

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(dynamic_component_parent.DynamicComponentParent, container)

    # Verify initial render
    assert container["children"][0]["attrs"]["text"] == "Target: my-value (v1)"

    # Update the dynamic target
    write_component(
        dynamic_path,
        """
        <label :text="display" />

        <script>
        import collagraph as cg

        class DynamicTarget(cg.Component):
            def init(self):
                val = self.props.get("target_prop", "missing")
                self.state["display"] = f"Target: {val} (v2)"
        </script>
        """,
    )

    # Trigger fine-grained reload
    changed_paths = {dynamic_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # Props should still be passed to the dynamic component
    assert container["children"][0]["attrs"]["text"] == "Target: my-value (v2)"


def test_vif_component_props_preserved(temp_dir):
    """Props on components with v-if should be preserved after reload."""
    # Create child component
    child_path = temp_dir / "vif_child.cgx"
    write_component(
        child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class VifChild(cg.Component):
            def init(self):
                msg = self.props.get("message", "missing")
                self.state["display_text"] = f"Msg: {msg} (v1)"
        </script>
        """,
    )

    # Create parent with v-if
    parent_path = temp_dir / "vif_parent.cgx"
    write_component(
        parent_path,
        """
        <widget>
            <VifChild v-if="show_child" :message="child_message" />
        </widget>

        <script>
        import collagraph as cg

        from vif_child import VifChild


        class VifParent(cg.Component):
            def init(self):
                self.state["show_child"] = True
                self.state["child_message"] = "Hello"
        </script>
        """,
    )

    import vif_parent

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(vif_parent.VifParent, container)

    # Verify initial render
    widget = container["children"][0]
    assert len(widget["children"]) == 1
    assert widget["children"][0]["attrs"]["text"] == "Msg: Hello (v1)"

    # Update the child component
    write_component(
        child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class VifChild(cg.Component):
            def init(self):
                msg = self.props.get("message", "missing")
                self.state["display_text"] = f"Msg: {msg} (v2)"
        </script>
        """,
    )

    # Trigger fine-grained reload
    changed_paths = {child_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # Dynamic prop should be preserved
    widget = container["children"][0]
    assert widget["children"][0]["attrs"]["text"] == "Msg: Hello (v2)"


def test_component_ref_reregistered_after_reload(temp_dir):
    """Component refs should be re-registered after hot reload."""
    # Create child component
    child_path = temp_dir / "ref_child.cgx"
    write_component(
        child_path,
        """
        <label text="Child v1" />

        <script>
        import collagraph as cg

        class RefChild(cg.Component):
            def get_version(self):
                return "v1"
        </script>
        """,
    )

    # Create parent with ref to child component
    parent_path = temp_dir / "ref_parent.cgx"
    write_component(
        parent_path,
        """
        <RefChild ref="child_ref" />

        <script>
        import collagraph as cg

        from ref_child import RefChild


        class RefParent(cg.Component):
            def get_child_version(self):
                if hasattr(self, "refs") and "child_ref" in self.refs:
                    return self.refs["child_ref"].get_version()
                return None
        </script>
        """,
    )

    import ref_parent

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(ref_parent.RefParent, container)

    # Verify ref is available
    parent_component = gui.fragment.component
    assert parent_component.get_child_version() == "v1"

    # Update the child component
    write_component(
        child_path,
        """
        <label text="Child v2" />

        <script>
        import collagraph as cg

        class RefChild(cg.Component):
            def get_version(self):
                return "v2"
        </script>
        """,
    )

    # Trigger fine-grained reload
    changed_paths = {child_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # Ref should be re-registered with the new component instance
    assert parent_component.get_child_version() == "v2"


def test_vbind_spread_props_preserved(temp_dir):
    """Props passed via v-bind spread should be preserved after reload.

    Note: v-bind spread is stored in _binds (not _attributes), so it IS preserved.
    This is because v-bind spread is treated as a dynamic binding.
    """
    # Create child component
    child_path = temp_dir / "spread_child.cgx"
    write_component(
        child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class SpreadChild(cg.Component):
            def init(self):
                a = self.props.get("prop_a", "missing")
                b = self.props.get("prop_b", "missing")
                self.state["display_text"] = f"A:{a} B:{b} (v1)"
        </script>
        """,
    )

    # Create parent using v-bind spread
    parent_path = temp_dir / "spread_parent.cgx"
    write_component(
        parent_path,
        """
        <SpreadChild v-bind="child_props" />

        <script>
        import collagraph as cg

        from spread_child import SpreadChild


        class SpreadParent(cg.Component):
            def init(self):
                self.state["child_props"] = {
                    "prop_a": "value-a",
                    "prop_b": "value-b",
                }
        </script>
        """,
    )

    import spread_parent

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(spread_parent.SpreadParent, container)

    # Verify initial render
    assert container["children"][0]["attrs"]["text"] == "A:value-a B:value-b (v1)"

    # Update the child component
    write_component(
        child_path,
        """
        <label :text="display_text" />

        <script>
        import collagraph as cg

        class SpreadChild(cg.Component):
            def init(self):
                a = self.props.get("prop_a", "missing")
                b = self.props.get("prop_b", "missing")
                self.state["display_text"] = f"A:{a} B:{b} (v2)"
        </script>
        """,
    )

    # Trigger fine-grained reload
    changed_paths = {child_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # Props from spread should be preserved
    assert container["children"][0]["attrs"]["text"] == "A:value-a B:value-b (v2)"


def test_multiple_events_preserved(temp_dir):
    """Multiple event handlers should all be preserved after reload."""
    # Create child component that can emit multiple events
    child_path = temp_dir / "multi_event_child.cgx"
    write_component(
        child_path,
        """
        <label text="Multi Event Child v1" />

        <script>
        import collagraph as cg

        class MultiEventChild(cg.Component):
            pass
        </script>
        """,
    )

    # Create parent with multiple event handlers
    parent_path = temp_dir / "multi_event_parent.cgx"
    write_component(
        parent_path,
        """
        <widget>
            <MultiEventChild
                @event-a="on_event_a"
                @event-b="on_event_b"
            />
            <label :text="status" />
        </widget>

        <script>
        import collagraph as cg

        from multi_event_child import MultiEventChild


        class MultiEventParent(cg.Component):
            def init(self):
                self.state["status"] = "none"

            def on_event_a(self, value):
                self.state["status"] = f"A:{value}"

            def on_event_b(self, value):
                self.state["status"] = f"B:{value}"
        </script>
        """,
    )

    import multi_event_parent

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )
    container = {"type": "root"}
    gui.render(multi_event_parent.MultiEventParent, container)

    def find_child_component(fragment):
        from collagraph.fragment import ComponentFragment, ListFragment

        if isinstance(fragment, ComponentFragment) and fragment.component:
            if type(fragment.component).__name__ == "MultiEventChild":
                return fragment

        # Check rendered_fragment for component usage sites
        if isinstance(fragment, ComponentFragment) and fragment.rendered_fragment:
            result = find_child_component(fragment.rendered_fragment)
            if result:
                return result

        # Check slot_content
        if isinstance(fragment, ComponentFragment):
            for slot_fragments in fragment.slot_content.values():
                for child in slot_fragments:
                    result = find_child_component(child)
                    if result:
                        return result

        # Check generated fragments for ListFragment
        if isinstance(fragment, ListFragment):
            for child in fragment._generated_fragments:
                result = find_child_component(child)
                if result:
                    return result

        # Check template_children
        for child in fragment.template_children:
            result = find_child_component(child)
            if result:
                return result
        return None

    # Test events work before reload
    child_fragment = find_child_component(gui.fragment)
    child_fragment.component.emit("event-a", "test1")
    widget = container["children"][0]
    label = widget["children"][1]
    assert label["attrs"]["text"] == "A:test1"

    child_fragment.component.emit("event-b", "test2")
    assert label["attrs"]["text"] == "B:test2"

    # Update the child component
    write_component(
        child_path,
        """
        <label text="Multi Event Child v2" />

        <script>
        import collagraph as cg

        class MultiEventChild(cg.Component):
            pass
        </script>
        """,
    )

    # Trigger fine-grained reload
    changed_paths = {child_path.resolve()}
    result = gui._hot_reloader._reload_changed_files(
        changed_paths, preserve_state=False
    )
    assert result is True

    # Both event handlers should still work
    child_fragment = find_child_component(gui.fragment)
    child_fragment.component.emit("event-a", "after-reload-a")
    assert label["attrs"]["text"] == "A:after-reload-a"

    child_fragment.component.emit("event-b", "after-reload-b")
    assert label["attrs"]["text"] == "B:after-reload-b"
