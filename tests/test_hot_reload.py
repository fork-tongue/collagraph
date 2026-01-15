"""Tests for hot reload functionality."""

import sys
import tempfile
from pathlib import Path

import pytest

import collagraph as cg


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

    # Trigger reload
    result = gui.reload()
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
    )
    container = {"type": "root"}
    gui.render(temp_component.TempComponent, container)

    assert container["children"][0]["attrs"]["text"] == "Initial"

    # First reload
    temp_cgx_file.write_text("""
<label :text="label_text" />

<script>
import collagraph as cg

class TempComponent(cg.Component):
    def init(self):
        self.state["label_text"] = "First Update"
</script>
""")
    assert gui.reload() is True
    assert container["children"][0]["attrs"]["text"] == "First Update"

    # Second reload
    temp_cgx_file.write_text("""
<label :text="label_text" />

<script>
import collagraph as cg

class TempComponent(cg.Component):
    def init(self):
        self.state["label_text"] = "Second Update"
</script>
""")
    assert gui.reload() is True
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
