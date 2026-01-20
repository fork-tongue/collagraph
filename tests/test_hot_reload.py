"""Tests for hot reload functionality."""

import sys
import tempfile
from pathlib import Path

import pytest

import collagraph as cg
from collagraph.sfc.importer import _loaded_cgx_modules


@pytest.fixture
def temp_cgx_file():
    """Create a temporary .cgx file that can be modified during tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cgx_path = Path(tmpdir) / "temp_component.cgx"

        # Initial component content
        initial_content = """
<label :text="label_text" />

<script>
import collagraph as cg

class TempComponent(cg.Component):
    def init(self):
        self.state["label_text"] = "Initial"
</script>
"""
        cgx_path.write_text(initial_content)

        # Add tmpdir to sys.path so the module can be imported
        sys.path.insert(0, tmpdir)

        yield cgx_path

        # Cleanup
        sys.path.remove(tmpdir)
        # Remove from sys.modules if it was imported
        for name in list(sys.modules.keys()):
            if name.startswith("temp_component"):
                del sys.modules[name]


def test_reload_returns_false_when_not_enabled(parse_source):
    """Test that reload() returns False when hot_reload is not enabled."""
    App, _ = parse_source(
        """
        <app/>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=False,
    )
    container = {"type": "root"}
    gui.render(App, container)

    # reload() should return False when hot_reload is not enabled
    assert gui.reload() is False


def test_reload_updates_ui(temp_cgx_file):
    """Test that reload() updates the UI with new component content."""
    # Import the component
    import temp_component

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,  # Disable watchdog to avoid inotify issues on CI
    )
    container = {"type": "root"}
    gui.render(temp_component.TempComponent, container)

    # Verify initial render
    label = container["children"][0]
    assert label["type"] == "label"
    assert label["attrs"]["text"] == "Initial"

    # Modify the component file
    new_content = """
<label :text="label_text" />

<script>
import collagraph as cg

class TempComponent(cg.Component):
    def init(self):
        self.state["label_text"] = "Updated"
</script>
"""
    temp_cgx_file.write_text(new_content)

    # Trigger reload WITHOUT state preservation to test that code changes work
    result = gui.reload(preserve_state=False)
    assert result is True

    # Verify the UI was updated
    label = container["children"][0]
    assert label["attrs"]["text"] == "Updated"


def test_reload_handles_syntax_error(temp_cgx_file):
    """Test that reload() handles syntax errors gracefully."""
    import temp_component

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,  # Disable watchdog to avoid inotify issues on CI
    )
    container = {"type": "root"}
    gui.render(temp_component.TempComponent, container)

    # Verify initial render
    label = container["children"][0]
    assert label["attrs"]["text"] == "Initial"

    # Write invalid Python syntax
    invalid_content = """
<label :text="label_text" />

<script>
import collagraph as cg

class TempComponent(cg.Component):
    def init(self)  # Missing colon - syntax error
        self.state["label_text"] = "Updated"
</script>
"""
    temp_cgx_file.write_text(invalid_content)

    # Reload should fail but keep old UI
    result = gui.reload()
    assert result is False

    # UI should still show the old content
    label = container["children"][0]
    assert label["attrs"]["text"] == "Initial"


def test_reload_handles_runtime_error(temp_cgx_file):
    """Test that reload() handles runtime errors in component init."""
    import temp_component

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,  # Disable watchdog to avoid inotify issues on CI
    )
    container = {"type": "root"}
    gui.render(temp_component.TempComponent, container)

    # Verify initial render
    label = container["children"][0]
    assert label["attrs"]["text"] == "Initial"

    # Write content that will raise an error during init
    error_content = """
<label :text="label_text" />

<script>
import collagraph as cg

class TempComponent(cg.Component):
    def init(self):
        raise RuntimeError("Intentional error")
</script>
"""
    temp_cgx_file.write_text(error_content)

    # Reload should fail during re-render
    result = gui.reload()
    assert result is False


def test_reload_with_changed_template(temp_cgx_file):
    """Test that reload() handles template changes."""
    import temp_component

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,  # Disable watchdog to avoid inotify issues on CI
    )
    container = {"type": "root"}
    gui.render(temp_component.TempComponent, container)

    # Verify initial render - single label
    assert len(container["children"]) == 1
    assert container["children"][0]["type"] == "label"

    # Change template to have different structure
    new_content = """
<widget>
    <label text="First" />
    <label text="Second" />
</widget>

<script>
import collagraph as cg

class TempComponent(cg.Component):
    pass
</script>
"""
    temp_cgx_file.write_text(new_content)

    # Trigger reload
    result = gui.reload()
    assert result is True

    # Verify new structure
    widget = container["children"][0]
    assert widget["type"] == "widget"
    assert len(widget["children"]) == 2
    assert widget["children"][0]["attrs"]["text"] == "First"
    assert widget["children"][1]["attrs"]["text"] == "Second"


def test_multiple_reloads(temp_cgx_file):
    """Test that multiple consecutive reloads work correctly."""
    import temp_component

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,  # Disable watchdog to avoid inotify issues on CI
    )
    container = {"type": "root"}
    gui.render(temp_component.TempComponent, container)

    assert container["children"][0]["attrs"]["text"] == "Initial"

    # First reload - without state preservation to test code changes
    temp_cgx_file.write_text("""
<label :text="label_text" />

<script>
import collagraph as cg

class TempComponent(cg.Component):
    def init(self):
        self.state["label_text"] = "First Update"
</script>
""")
    assert gui.reload(preserve_state=False) is True
    assert container["children"][0]["attrs"]["text"] == "First Update"

    # Second reload - without state preservation to test code changes
    temp_cgx_file.write_text("""
<label :text="label_text" />

<script>
import collagraph as cg

class TempComponent(cg.Component):
    def init(self):
        self.state["label_text"] = "Second Update"
</script>
""")
    assert gui.reload(preserve_state=False) is True
    assert container["children"][0]["attrs"]["text"] == "Second Update"

    # Third reload with error - should keep second update
    temp_cgx_file.write_text("""
<label :text="label_text" />

<script>
import collagraph as cg

class TempComponent(cg.Component):
    def init(self):
        raise ValueError("oops")
</script>
""")
    assert gui.reload() is False
    # Content should still be from second update (before the error)
    # Note: The label won't exist anymore because we unmount before the error
    # This is a known limitation - errors during re-render are problematic


# =============================================================================
# State Preservation Tests
# =============================================================================


def test_state_preserved_across_reload(temp_cgx_file):
    """Test that component state is preserved across reload by default."""
    import temp_component

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,  # Disable watchdog to avoid inotify issues on CI
    )
    container = {"type": "root"}
    gui.render(temp_component.TempComponent, container)

    # Verify initial render
    assert container["children"][0]["attrs"]["text"] == "Initial"

    # Modify the component's state directly (simulating user interaction)
    gui.fragment.component.state["label_text"] = "User Modified"
    assert container["children"][0]["attrs"]["text"] == "User Modified"

    # Reload with same component code (state should be preserved)
    # The file content doesn't change, we're just reloading
    result = gui.reload(preserve_state=True)
    assert result is True

    # State should be preserved - still "User Modified", not reset to "Initial"
    assert container["children"][0]["attrs"]["text"] == "User Modified"


def test_state_not_preserved_when_disabled(temp_cgx_file):
    """Test that state is reset when preserve_state=False."""
    import temp_component

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,  # Disable watchdog to avoid inotify issues on CI
    )
    container = {"type": "root"}
    gui.render(temp_component.TempComponent, container)

    # Modify the component's state
    gui.fragment.component.state["label_text"] = "User Modified"
    assert container["children"][0]["attrs"]["text"] == "User Modified"

    # Reload WITHOUT state preservation
    result = gui.reload(preserve_state=False)
    assert result is True

    # State should be reset to initial value from init()
    assert container["children"][0]["attrs"]["text"] == "Initial"


def test_state_preserved_with_new_state_keys(temp_cgx_file):
    """Test that new state keys are added while preserving existing ones."""
    import temp_component

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,  # Disable watchdog to avoid inotify issues on CI
    )
    container = {"type": "root"}
    gui.render(temp_component.TempComponent, container)

    # Modify state
    gui.fragment.component.state["label_text"] = "Preserved"

    # Update component to add a new state key
    new_content = """
<widget>
    <label :text="label_text" />
    <label :text="new_text" />
</widget>

<script>
import collagraph as cg

class TempComponent(cg.Component):
    def init(self):
        self.state["label_text"] = "Default"
        self.state["new_text"] = "New Key"
</script>
"""
    temp_cgx_file.write_text(new_content)

    result = gui.reload(preserve_state=True)
    assert result is True

    # Old key should be preserved
    widget = container["children"][0]
    assert widget["children"][0]["attrs"]["text"] == "Preserved"
    # New key should have its default value
    assert widget["children"][1]["attrs"]["text"] == "New Key"


def test_state_preserved_with_multiple_state_keys(temp_cgx_file):
    """Test that state preservation works with multiple state keys."""
    # Create a component with multiple state keys
    initial_content = """
<widget>
    <label :text="name" />
    <label :text="count" />
</widget>

<script>
import collagraph as cg

class MultiState(cg.Component):
    def init(self):
        self.state["name"] = "initial_name"
        self.state["count"] = 0
        self.state["flag"] = False
</script>
"""
    temp_cgx_file.write_text(initial_content)

    # Clear module cache from previous tests
    for name in list(sys.modules.keys()):
        if name.startswith("temp_component"):
            del sys.modules[name]

    import temp_component

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,  # Disable watchdog to avoid inotify issues on CI
    )
    container = {"type": "root"}
    gui.render(temp_component.MultiState, container)

    # Modify multiple state keys
    gui.fragment.component.state["name"] = "modified_name"
    gui.fragment.component.state["count"] = 42
    gui.fragment.component.state["flag"] = True

    # Reload with state preservation
    result = gui.reload(preserve_state=True)
    assert result is True

    # All state keys should be preserved
    assert gui.fragment.component.state["name"] == "modified_name"
    assert gui.fragment.component.state["count"] == 42
    assert gui.fragment.component.state["flag"] is True


# =============================================================================
# Dynamic Component Import Watching Tests
# =============================================================================


def test_watches_dynamically_imported_components():
    """
    Test that hot reload watches CGX components imported by a parent component,
    even when those components are not currently rendered.

    This tests the scenario where:
    - A parent component (scene_item.cgx) imports child components (volume.cgx,
        mesh.cgx)
    - The parent uses :is="type_map(obj_type)" to dynamically select which to render
    - If no items of type "volume" exist, volume.cgx is never in the fragment tree
    - But volume.cgx should still be watched for hot reload

    See: https://github.com/user/arbiter-one - scene_item.cgx imports volume.cgx,
    landmark.cgx, mesh.cgx but they aren't watched because they're not rendered.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create child component A (like volume.cgx)
        child_a_path = tmpdir / "child_a.cgx"
        child_a_path.write_text("""
<label text="Child A" />

<script>
import collagraph as cg

class ChildA(cg.Component):
    pass
</script>
""")

        # Create child component B (like mesh.cgx)
        child_b_path = tmpdir / "child_b.cgx"
        child_b_path.write_text("""
<label text="Child B" />

<script>
import collagraph as cg

class ChildB(cg.Component):
    pass
</script>
""")

        # Create parent component that imports both but only renders one dynamically
        parent_path = tmpdir / "parent_component.cgx"
        parent_path.write_text("""
<component
    v-if="show_child"
    :is="type_map(child_type)"
/>

<script>
import collagraph as cg

from child_a import ChildA
from child_b import ChildB


def type_map(child_type):
    return {
        "a": ChildA,
        "b": ChildB,
    }[child_type]


class ParentComponent(cg.Component):
    pass
</script>
""")

        # Add tmpdir to sys.path
        sys.path.insert(0, str(tmpdir))

        try:
            # Clear any previous CGX modules
            _loaded_cgx_modules.clear()

            import parent_component

            # Render with show_child=False, so no child component is rendered
            gui = cg.Collagraph(
                renderer=cg.DictRenderer(),
                event_loop_type=cg.EventLoopType.SYNC,
                hot_reload=True,
                hot_reload_watchdog=False,
            )
            container = {"type": "root"}
            state = {"show_child": False, "child_type": "a"}
            gui.render(parent_component.ParentComponent, container, state=state)

            # Get the paths that are being watched
            watched_paths = set(gui._hot_reloader._watched_modules.keys())

            # Parent should be watched (it's rendered)
            assert parent_path.resolve() in watched_paths, (
                f"Parent component should be watched. Watched: {watched_paths}"
            )

            # Child components should ALSO be watched, even though not rendered
            # This is the bug - currently they are NOT watched
            assert child_a_path.resolve() in watched_paths, (
                "ChildA should be watched even when not rendered. "
                f"Watched: {watched_paths}"
            )
            assert child_b_path.resolve() in watched_paths, (
                "ChildB should be watched even when not rendered. "
                f"Watched: {watched_paths}"
            )

        finally:
            # Cleanup
            sys.path.remove(str(tmpdir))
            for name in list(sys.modules.keys()):
                if name in ("parent_component", "child_a", "child_b"):
                    del sys.modules[name]
            _loaded_cgx_modules.clear()


def test_watches_nested_dynamic_imports():
    """
    Test that hot reload watches CGX components imported transitively.

    Scenario:
    - root.cgx imports parent.cgx
    - parent.cgx imports child.cgx (dynamically used)
    - child.cgx should be watched even if not rendered
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create leaf component
        leaf_path = tmpdir / "leaf_comp.cgx"
        leaf_path.write_text("""
<label text="Leaf" />

<script>
import collagraph as cg

class LeafComp(cg.Component):
    pass
</script>
""")

        # Create middle component that imports leaf
        middle_path = tmpdir / "middle_comp.cgx"
        middle_path.write_text("""
<component v-if="show" :is="get_leaf()" />

<script>
import collagraph as cg

from leaf_comp import LeafComp


def get_leaf():
    return LeafComp


class MiddleComp(cg.Component):
    pass
</script>
""")

        # Create root component
        root_path = tmpdir / "root_comp.cgx"
        root_path.write_text("""
<MiddleComp :show="False" />

<script>
import collagraph as cg

from middle_comp import MiddleComp


class RootComp(cg.Component):
    pass
</script>
""")

        sys.path.insert(0, str(tmpdir))

        try:
            _loaded_cgx_modules.clear()

            import root_comp

            gui = cg.Collagraph(
                renderer=cg.DictRenderer(),
                event_loop_type=cg.EventLoopType.SYNC,
                hot_reload=True,
                hot_reload_watchdog=False,
            )
            container = {"type": "root"}
            gui.render(root_comp.RootComp, container)

            watched_paths = set(gui._hot_reloader._watched_modules.keys())

            # All three should be watched
            assert root_path.resolve() in watched_paths
            assert middle_path.resolve() in watched_paths
            # Leaf should be watched even though show=False means it's not rendered
            assert leaf_path.resolve() in watched_paths, (
                f"LeafComp should be watched transitively. Watched: {watched_paths}"
            )

        finally:
            sys.path.remove(str(tmpdir))
            for name in list(sys.modules.keys()):
                if name in ("root_comp", "middle_comp", "leaf_comp"):
                    del sys.modules[name]
            _loaded_cgx_modules.clear()


def test_finds_affected_fragments_in_dynamic_components():
    """
    Test that hot reload correctly finds affected fragments when a component
    is rendered inside a dynamic component (:is directive).

    This tests the scenario where:
    - A parent component uses <component :is="type_map(obj_type)" />
    - The dynamic component renders a child (e.g., Volume)
    - When volume.cgx changes, the Volume component should be found as affected

    The issue was that _find_affected_recursive only looked at fragment.children,
    but DynamicFragment stores its active component in _active_fragment.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create child component (like volume.cgx)
        child_path = tmpdir / "dynamic_child.cgx"
        child_path.write_text("""
<label text="Dynamic Child" />

<script>
import collagraph as cg

class DynamicChild(cg.Component):
    pass
</script>
""")

        # Create parent that uses dynamic component
        parent_path = tmpdir / "dynamic_parent.cgx"
        parent_path.write_text("""
<component :is="get_child()" />

<script>
import collagraph as cg

from dynamic_child import DynamicChild


def get_child():
    return DynamicChild


class DynamicParent(cg.Component):
    pass
</script>
""")

        sys.path.insert(0, str(tmpdir))

        try:
            _loaded_cgx_modules.clear()

            import dynamic_parent

            gui = cg.Collagraph(
                renderer=cg.DictRenderer(),
                event_loop_type=cg.EventLoopType.SYNC,
                hot_reload=True,
                hot_reload_watchdog=False,
            )
            container = {"type": "root"}
            gui.render(dynamic_parent.DynamicParent, container)

            # Verify the child is rendered
            assert container["children"][0]["type"] == "label"
            assert container["children"][0]["attrs"]["text"] == "Dynamic Child"

            # Now simulate finding affected fragments when dynamic_child changes
            changed_modules = {"dynamic_child"}
            affected = gui._hot_reloader._find_affected_fragments(
                gui.fragment, changed_modules
            )

            # The DynamicChild component should be found as affected
            assert len(affected) > 0, (
                f"DynamicChild should be found as affected. "
                f"Fragment tree: {gui.fragment.debug()}"
            )

            # Verify it's the right component
            affected_modules = {type(f.component).__module__ for f in affected}
            assert "dynamic_child" in affected_modules, (
                f"dynamic_child module should be in affected. Got: {affected_modules}"
            )

        finally:
            sys.path.remove(str(tmpdir))
            for name in list(sys.modules.keys()):
                if name in ("dynamic_parent", "dynamic_child"):
                    del sys.modules[name]
            _loaded_cgx_modules.clear()


def test_finds_affected_fragments_in_component_fragment():
    """
    Test that hot reload correctly finds affected fragments inside a
    ComponentFragment's rendered content (fragment attribute).

    ComponentFragment has both 'children' (slot contents) and 'fragment'
    (the component's rendered template). We need to traverse both.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create grandchild component
        grandchild_path = tmpdir / "grandchild_comp.cgx"
        grandchild_path.write_text("""
<label text="Grandchild" />

<script>
import collagraph as cg

class GrandchildComp(cg.Component):
    pass
</script>
""")

        # Create child that renders grandchild
        child_path = tmpdir / "child_comp.cgx"
        child_path.write_text("""
<GrandchildComp />

<script>
import collagraph as cg

from grandchild_comp import GrandchildComp


class ChildComp(cg.Component):
    pass
</script>
""")

        # Create parent
        parent_path = tmpdir / "parent_comp.cgx"
        parent_path.write_text("""
<ChildComp />

<script>
import collagraph as cg

from child_comp import ChildComp


class ParentComp(cg.Component):
    pass
</script>
""")

        sys.path.insert(0, str(tmpdir))

        try:
            _loaded_cgx_modules.clear()

            import parent_comp

            gui = cg.Collagraph(
                renderer=cg.DictRenderer(),
                event_loop_type=cg.EventLoopType.SYNC,
                hot_reload=True,
                hot_reload_watchdog=False,
            )
            container = {"type": "root"}
            gui.render(parent_comp.ParentComp, container)

            # Verify rendering
            assert container["children"][0]["type"] == "label"

            # Find affected when grandchild changes
            changed_modules = {"grandchild_comp"}
            affected = gui._hot_reloader._find_affected_fragments(
                gui.fragment, changed_modules
            )

            assert len(affected) > 0, "GrandchildComp should be found as affected"

            affected_modules = {type(f.component).__module__ for f in affected}
            assert "grandchild_comp" in affected_modules

        finally:
            sys.path.remove(str(tmpdir))
            for name in list(sys.modules.keys()):
                if name in ("parent_comp", "child_comp", "grandchild_comp"):
                    del sys.modules[name]
            _loaded_cgx_modules.clear()


def test_finds_affected_fragments_in_vfor_with_dynamic():
    """
    Test that hot reload finds affected fragments in v-for loops
    that contain dynamic components.

    This mimics the Arbiter-ONE scenario:
    - scene.cgx has v-for="item in items"
    - Each item renders <component :is="type_map(item.type)" />
    - The type_map returns Volume, Mesh, etc.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create item component (like volume.cgx)
        item_path = tmpdir / "item_comp.cgx"
        item_path.write_text("""
<label :text="props.get('name', 'item')" />

<script>
import collagraph as cg

class ItemComp(cg.Component):
    pass
</script>
""")

        # Create list component with v-for and dynamic component
        list_path = tmpdir / "list_comp.cgx"
        list_path.write_text("""
<widget>
    <component
        v-for="item in items"
        :is="get_comp()"
        :name="item"
    />
</widget>

<script>
import collagraph as cg

from item_comp import ItemComp


def get_comp():
    return ItemComp


class ListComp(cg.Component):
    pass
</script>
""")

        sys.path.insert(0, str(tmpdir))

        try:
            _loaded_cgx_modules.clear()

            import list_comp

            gui = cg.Collagraph(
                renderer=cg.DictRenderer(),
                event_loop_type=cg.EventLoopType.SYNC,
                hot_reload=True,
                hot_reload_watchdog=False,
            )
            container = {"type": "root"}
            state = {"items": ["one", "two", "three"]}
            gui.render(list_comp.ListComp, container, state=state)

            # Verify rendering - should have 3 labels
            widget = container["children"][0]
            assert len(widget["children"]) == 3
            assert widget["children"][0]["attrs"]["text"] == "one"

            # Find affected when item_comp changes
            changed_modules = {"item_comp"}
            affected = gui._hot_reloader._find_affected_fragments(
                gui.fragment, changed_modules
            )

            # Should find all 3 ItemComp instances
            assert len(affected) == 3, (
                f"Should find 3 affected ItemComp instances, found {len(affected)}"
            )

            affected_modules = {type(f.component).__module__ for f in affected}
            assert "item_comp" in affected_modules

        finally:
            sys.path.remove(str(tmpdir))
            for name in list(sys.modules.keys()):
                if name in ("list_comp", "item_comp"):
                    del sys.modules[name]
            _loaded_cgx_modules.clear()


def test_remount_fragment_inside_dynamic_component():
    """
    Test that hot reload can remount a fragment that is inside a DynamicFragment.

    The issue was that _remount_fragment tried to find the fragment in
    parent.children, but DynamicFragment stores its active component in
    _active_fragment, not in children.

    This caused: ValueError: <ComponentFragment(...)> is not in list
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create child component (like volume.cgx)
        child_path = tmpdir / "remount_child.cgx"
        child_path.write_text("""
<label :text="label_text" />

<script>
import collagraph as cg

class RemountChild(cg.Component):
    def init(self):
        self.state["label_text"] = "Initial"
</script>
""")

        # Create parent that uses dynamic component
        parent_path = tmpdir / "remount_parent.cgx"
        parent_path.write_text("""
<component :is="get_child()" />

<script>
import collagraph as cg

from remount_child import RemountChild


def get_child():
    return RemountChild


class RemountParent(cg.Component):
    pass
</script>
""")

        sys.path.insert(0, str(tmpdir))

        try:
            _loaded_cgx_modules.clear()

            import remount_parent

            gui = cg.Collagraph(
                renderer=cg.DictRenderer(),
                event_loop_type=cg.EventLoopType.SYNC,
                hot_reload=True,
                hot_reload_watchdog=False,
            )
            container = {"type": "root"}
            gui.render(remount_parent.RemountParent, container)

            # Verify initial render
            assert container["children"][0]["type"] == "label"
            assert container["children"][0]["attrs"]["text"] == "Initial"

            # Modify the child component
            child_path.write_text("""
<label :text="label_text" />

<script>
import collagraph as cg

class RemountChild(cg.Component):
    def init(self):
        self.state["label_text"] = "Updated"
</script>
""")

            # Trigger fine-grained reload - this should NOT raise ValueError
            # We call _reload_changed_files directly to test the fine-grained path
            changed_paths = {child_path.resolve()}
            result = gui._hot_reloader._reload_changed_files(
                changed_paths, preserve_state=False
            )
            assert result is True, "Fine-grained reload should succeed"

            # Verify the UI was updated
            assert container["children"][0]["attrs"]["text"] == "Updated"

        finally:
            sys.path.remove(str(tmpdir))
            for name in list(sys.modules.keys()):
                if name in ("remount_parent", "remount_child"):
                    del sys.modules[name]
            _loaded_cgx_modules.clear()


def test_remount_fragment_in_vfor_with_dynamic():
    """
    Test that hot reload can remount fragments inside v-for with dynamic components.

    This is the full Arbiter-ONE scenario where scene_item.cgx uses v-for
    with dynamic components, and changing volume.cgx should trigger a reload.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create item component
        item_path = tmpdir / "vfor_item.cgx"
        item_path.write_text("""
<label :text="props.get('name', 'default') + ' - v1'" />

<script>
import collagraph as cg

class VforItem(cg.Component):
    pass
</script>
""")

        # Create list component with v-for and dynamic component
        list_path = tmpdir / "vfor_list.cgx"
        list_path.write_text("""
<widget>
    <component
        v-for="item in items"
        :is="get_comp()"
        :name="item"
    />
</widget>

<script>
import collagraph as cg

from vfor_item import VforItem


def get_comp():
    return VforItem


class VforList(cg.Component):
    pass
</script>
""")

        sys.path.insert(0, str(tmpdir))

        try:
            _loaded_cgx_modules.clear()

            import vfor_list

            gui = cg.Collagraph(
                renderer=cg.DictRenderer(),
                event_loop_type=cg.EventLoopType.SYNC,
                hot_reload=True,
                hot_reload_watchdog=False,
            )
            container = {"type": "root"}
            state = {"items": ["one", "two", "three"]}
            gui.render(vfor_list.VforList, container, state=state)

            # Verify initial render
            widget = container["children"][0]
            assert len(widget["children"]) == 3
            assert widget["children"][0]["attrs"]["text"] == "one - v1"
            assert widget["children"][1]["attrs"]["text"] == "two - v1"
            assert widget["children"][2]["attrs"]["text"] == "three - v1"

            # Modify the item component
            item_path.write_text("""
<label :text="props.get('name', 'default') + ' - v2'" />

<script>
import collagraph as cg

class VforItem(cg.Component):
    pass
</script>
""")

            # Trigger fine-grained reload - this should NOT raise ValueError
            # We call _reload_changed_files directly to test the fine-grained path
            changed_paths = {item_path.resolve()}
            result = gui._hot_reloader._reload_changed_files(
                changed_paths, preserve_state=False
            )
            assert result is True, "Fine-grained reload should succeed"

            # Verify the UI was updated
            widget = container["children"][0]
            assert len(widget["children"]) == 3
            assert widget["children"][0]["attrs"]["text"] == "one - v2"
            assert widget["children"][1]["attrs"]["text"] == "two - v2"
            assert widget["children"][2]["attrs"]["text"] == "three - v2"

        finally:
            sys.path.remove(str(tmpdir))
            for name in list(sys.modules.keys()):
                if name in ("vfor_list", "vfor_item"):
                    del sys.modules[name]
            _loaded_cgx_modules.clear()


def test_remount_multiple_fragments_inside_slot_content():
    """
    Test that hot reload can remount multiple fragments inside slot contents
    while preserving their order.

    ComponentFragment stores slot contents in slot_contents, not children.
    When remounting, we need to find the correct anchor from slot_contents.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create components that will be passed as slot content
        slot_child_a_path = tmpdir / "slot_child_a.cgx"
        slot_child_a_path.write_text("""
<label text="Child A v1" />

<script>
import collagraph as cg

class SlotChildA(cg.Component):
    pass
</script>
""")

        slot_child_b_path = tmpdir / "slot_child_b.cgx"
        slot_child_b_path.write_text("""
<label text="Child B v1" />

<script>
import collagraph as cg

class SlotChildB(cg.Component):
    pass
</script>
""")

        slot_child_c_path = tmpdir / "slot_child_c.cgx"
        slot_child_c_path.write_text("""
<label text="Child C v1" />

<script>
import collagraph as cg

class SlotChildC(cg.Component):
    pass
</script>
""")

        # Create a wrapper component with a slot
        wrapper_path = tmpdir / "multi_slot_wrapper.cgx"
        wrapper_path.write_text("""
<widget>
    <slot />
</widget>

<script>
import collagraph as cg

class MultiSlotWrapper(cg.Component):
    pass
</script>
""")

        # Create parent that uses the wrapper with multiple slot children
        parent_path = tmpdir / "multi_slot_parent.cgx"
        parent_path.write_text("""
<MultiSlotWrapper>
    <SlotChildA />
    <SlotChildB />
    <SlotChildC />
</MultiSlotWrapper>

<script>
import collagraph as cg

from multi_slot_wrapper import MultiSlotWrapper
from slot_child_a import SlotChildA
from slot_child_b import SlotChildB
from slot_child_c import SlotChildC


class MultiSlotParent(cg.Component):
    pass
</script>
""")

        sys.path.insert(0, str(tmpdir))

        try:
            _loaded_cgx_modules.clear()

            import multi_slot_parent

            gui = cg.Collagraph(
                renderer=cg.DictRenderer(),
                event_loop_type=cg.EventLoopType.SYNC,
                hot_reload=True,
                hot_reload_watchdog=False,
            )
            container = {"type": "root"}
            gui.render(multi_slot_parent.MultiSlotParent, container)

            # Verify initial render - order should be A, B, C
            widget = container["children"][0]
            assert widget["type"] == "widget"
            assert len(widget["children"]) == 3
            assert widget["children"][0]["attrs"]["text"] == "Child A v1"
            assert widget["children"][1]["attrs"]["text"] == "Child B v1"
            assert widget["children"][2]["attrs"]["text"] == "Child C v1"

            # Modify the middle child (B)
            slot_child_b_path.write_text("""
<label text="Child B v2" />

<script>
import collagraph as cg

class SlotChildB(cg.Component):
    pass
</script>
""")

            # Trigger fine-grained reload
            changed_paths = {slot_child_b_path.resolve()}
            result = gui._hot_reloader._reload_changed_files(
                changed_paths, preserve_state=False
            )
            assert result is True, "Fine-grained reload should succeed for slot content"

            # Verify the UI was updated AND order is preserved (A, B, C)
            widget = container["children"][0]
            assert len(widget["children"]) == 3
            assert widget["children"][0]["attrs"]["text"] == "Child A v1", (
                "A should still be first"
            )
            assert widget["children"][1]["attrs"]["text"] == "Child B v2", (
                "B should be updated and still second"
            )
            assert widget["children"][2]["attrs"]["text"] == "Child C v1", (
                "C should still be third"
            )

        finally:
            sys.path.remove(str(tmpdir))
            for name in list(sys.modules.keys()):
                if name in (
                    "multi_slot_parent",
                    "multi_slot_wrapper",
                    "slot_child_a",
                    "slot_child_b",
                    "slot_child_c",
                ):
                    del sys.modules[name]
            _loaded_cgx_modules.clear()


def test_remount_fragment_inside_slot_content():
    """
    Test that hot reload can remount a fragment that is inside slot contents.

    ComponentFragment stores slot contents in slot_contents, not children.
    This tests that _remount_fragment handles this case correctly.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create a component that will be passed as slot content
        slot_child_path = tmpdir / "slot_child.cgx"
        slot_child_path.write_text("""
<label text="Slot Child v1" />

<script>
import collagraph as cg

class SlotChild(cg.Component):
    pass
</script>
""")

        # Create a wrapper component with a slot
        wrapper_path = tmpdir / "slot_wrapper.cgx"
        wrapper_path.write_text("""
<widget>
    <slot />
</widget>

<script>
import collagraph as cg

class SlotWrapper(cg.Component):
    pass
</script>
""")

        # Create parent that uses the wrapper with slot content
        parent_path = tmpdir / "slot_parent.cgx"
        parent_path.write_text("""
<SlotWrapper>
    <SlotChild />
</SlotWrapper>

<script>
import collagraph as cg

from slot_wrapper import SlotWrapper
from slot_child import SlotChild


class SlotParent(cg.Component):
    pass
</script>
""")

        sys.path.insert(0, str(tmpdir))

        try:
            _loaded_cgx_modules.clear()

            import slot_parent

            gui = cg.Collagraph(
                renderer=cg.DictRenderer(),
                event_loop_type=cg.EventLoopType.SYNC,
                hot_reload=True,
                hot_reload_watchdog=False,
            )
            container = {"type": "root"}
            gui.render(slot_parent.SlotParent, container)

            # Verify initial render
            widget = container["children"][0]
            assert widget["type"] == "widget"
            assert widget["children"][0]["type"] == "label"
            assert widget["children"][0]["attrs"]["text"] == "Slot Child v1"

            # Modify the slot child component
            slot_child_path.write_text("""
<label text="Slot Child v2" />

<script>
import collagraph as cg

class SlotChild(cg.Component):
    pass
</script>
""")

            # Trigger fine-grained reload - this should NOT raise ValueError
            changed_paths = {slot_child_path.resolve()}
            result = gui._hot_reloader._reload_changed_files(
                changed_paths, preserve_state=False
            )
            assert result is True, "Fine-grained reload should succeed for slot content"

            # Verify the UI was updated
            widget = container["children"][0]
            assert widget["children"][0]["attrs"]["text"] == "Slot Child v2"

        finally:
            sys.path.remove(str(tmpdir))
            for name in list(sys.modules.keys()):
                if name in ("slot_parent", "slot_wrapper", "slot_child"):
                    del sys.modules[name]
            _loaded_cgx_modules.clear()
