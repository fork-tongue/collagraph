"""Tests for hot reload of pure-Python view components."""

import importlib.util
import sys
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

import collagraph as cg

VIEW_COMPONENT_TEMPLATE = """
import collagraph as cg
from collagraph import h


class TempViewComponent(cg.Component):
    def init(self):
        self.state["label_text"] = "{text}"

    def view(self):
        h.label(text=lambda: self.state["label_text"])
"""


@pytest.fixture
def temp_view_module():
    """Create a temporary .py view component module that can be modified."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_path = Path(tmpdir) / "temp_view_component.py"
        module_path.write_text(
            dedent(VIEW_COMPONENT_TEMPLATE.format(text="Initial")).lstrip()
        )

        sys.path.insert(0, tmpdir)

        yield module_path

        sys.path.remove(tmpdir)
        for name in list(sys.modules.keys()):
            if name.startswith("temp_view_component"):
                del sys.modules[name]


def make_gui():
    return cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
        hot_reload=True,
        hot_reload_watchdog=False,
    )


def test_view_module_is_watched(temp_view_module):
    """The .py file of a view component should end up in the watch list."""
    import temp_view_component

    gui = make_gui()
    container = {"type": "root"}
    gui.render(temp_view_component.TempViewComponent, container)

    watched = gui._hot_reloader._watched_modules
    assert watched.get(temp_view_module.resolve()) == "temp_view_component"


def test_full_reload_updates_ui(temp_view_module):
    """Full reload should pick up changes to a view component module."""
    import temp_view_component

    gui = make_gui()
    container = {"type": "root"}
    gui.render(temp_view_component.TempViewComponent, container)

    label = container["children"][0]
    assert label["type"] == "label"
    assert label["attrs"]["text"] == "Initial"

    temp_view_module.write_text(
        dedent(VIEW_COMPONENT_TEMPLATE.format(text="Updated")).lstrip()
    )

    assert gui.reload(preserve_state=False) is True

    label = container["children"][0]
    assert label["attrs"]["text"] == "Updated"


def test_full_reload_preserves_state(temp_view_module):
    """Component state should survive a reload when preserve_state is set."""
    import temp_view_component

    gui = make_gui()
    container = {"type": "root"}
    gui.render(temp_view_component.TempViewComponent, container)

    # Change state at runtime, as if the user interacted with the app
    gui.fragment.component.state["label_text"] = "Runtime"
    assert container["children"][0]["attrs"]["text"] == "Runtime"

    temp_view_module.write_text(
        dedent(VIEW_COMPONENT_TEMPLATE.format(text="Updated")).lstrip()
    )

    assert gui.reload(preserve_state=True) is True

    # The runtime state wins over the new init value
    assert container["children"][0]["attrs"]["text"] == "Runtime"


def test_full_reload_handles_syntax_error(temp_view_module):
    """A broken module should fail the reload and keep the old UI."""
    import temp_view_component

    gui = make_gui()
    container = {"type": "root"}
    gui.render(temp_view_component.TempViewComponent, container)

    temp_view_module.write_text("def broken(:\n")

    assert gui.reload() is False

    label = container["children"][0]
    assert label["attrs"]["text"] == "Initial"

    # A subsequent fix should reload fine
    temp_view_module.write_text(
        dedent(VIEW_COMPONENT_TEMPLATE.format(text="Fixed")).lstrip()
    )
    assert gui.reload(preserve_state=False) is True
    assert container["children"][0]["attrs"]["text"] == "Fixed"


def test_fine_grained_reload_of_view_child():
    """Changing a child view module should remount only that component."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        child_path = tmpdir_path / "view_child.py"
        child_path.write_text(
            dedent(
                """
                import collagraph as cg
                from collagraph import h


                class ViewChild(cg.Component):
                    def view(self):
                        h.label(text="child v1")
                """
            ).lstrip()
        )

        parent_path = tmpdir_path / "view_parent.py"
        parent_path.write_text(
            dedent(
                """
                import collagraph as cg
                from collagraph import h

                from view_child import ViewChild


                class ViewParent(cg.Component):
                    def view(self):
                        with h.widget():
                            h.label(text="parent")
                            h(ViewChild)
                """
            ).lstrip()
        )

        sys.path.insert(0, str(tmpdir_path))
        try:
            import view_parent

            gui = make_gui()
            container = {"type": "root"}
            gui.render(view_parent.ViewParent, container)

            widget = container["children"][0]
            assert widget["children"][0]["attrs"]["text"] == "parent"
            assert widget["children"][1]["attrs"]["text"] == "child v1"

            # Both modules should be watched
            watched = set(gui._hot_reloader._watched_modules.values())
            assert watched == {"view_parent", "view_child"}

            child_path.write_text(
                dedent(
                    """
                    import collagraph as cg
                    from collagraph import h


                    class ViewChild(cg.Component):
                        def view(self):
                            h.label(text="child v2")
                    """
                ).lstrip()
            )

            result = gui._hot_reloader._reload_changed_files(
                {child_path.resolve()}, preserve_state=False
            )
            assert result is True

            widget = container["children"][0]
            assert widget["children"][0]["attrs"]["text"] == "parent"
            assert widget["children"][1]["attrs"]["text"] == "child v2"

        finally:
            sys.path.remove(str(tmpdir_path))
            for name in ("view_parent", "view_child"):
                sys.modules.pop(name, None)


def test_cgx_root_with_view_child():
    """A .cgx root importing a Python view component should watch both files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        child_path = tmpdir_path / "mixed_view_child.py"
        child_path.write_text(
            dedent(
                """
                import collagraph as cg
                from collagraph import h


                class MixedViewChild(cg.Component):
                    def view(self):
                        h.label(text="child v1")
                """
            ).lstrip()
        )

        parent_path = tmpdir_path / "mixed_cgx_parent.cgx"
        parent_path.write_text(
            dedent(
                """
                <widget>
                  <MixedViewChild />
                </widget>

                <script>
                import collagraph as cg

                from mixed_view_child import MixedViewChild


                class MixedCgxParent(cg.Component):
                    pass
                </script>
                """
            ).lstrip()
        )

        sys.path.insert(0, str(tmpdir_path))
        try:
            import mixed_cgx_parent

            gui = make_gui()
            container = {"type": "root"}
            gui.render(mixed_cgx_parent.MixedCgxParent, container)

            widget = container["children"][0]
            assert widget["children"][0]["attrs"]["text"] == "child v1"

            watched = set(gui._hot_reloader._watched_modules.values())
            assert watched == {"mixed_cgx_parent", "mixed_view_child"}

            child_path.write_text(
                dedent(
                    """
                    import collagraph as cg
                    from collagraph import h


                    class MixedViewChild(cg.Component):
                        def view(self):
                            h.label(text="child v2")
                    """
                ).lstrip()
            )

            result = gui._hot_reloader._reload_changed_files(
                {child_path.resolve()}, preserve_state=False
            )
            assert result is True

            widget = container["children"][0]
            assert widget["children"][0]["attrs"]["text"] == "child v2"

        finally:
            sys.path.remove(str(tmpdir_path))
            for name in ("mixed_cgx_parent", "mixed_view_child"):
                sys.modules.pop(name, None)


MAIN_SCRIPT_TEMPLATE = """
import collagraph as cg
from collagraph import h

GUARD_RAN = False


class MainViewApp(cg.Component):
    def init(self):
        self.state["label_text"] = "{text}"

    def view(self):
        h.label(text=lambda: self.state["label_text"])


if __name__ == "__main__":
    GUARD_RAN = True
"""


def test_reload_of_main_script_module(monkeypatch):
    """Components defined in a script run as __main__ should hot reload.

    On reload, the script is re-executed under a substitute module name so
    that its ``if __name__ == "__main__"`` block does not run again.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "main_view_script.py"
        script_path.write_text(
            dedent(MAIN_SCRIPT_TEMPLATE.format(text="Initial")).lstrip()
        )

        # Load the script the way `python main_view_script.py` would:
        # as the __main__ module
        spec = importlib.util.spec_from_file_location("__main__", script_path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, "__main__", module)
        spec.loader.exec_module(module)
        assert module.GUARD_RAN is True
        assert module.MainViewApp.__module__ == "__main__"

        try:
            gui = make_gui()
            container = {"type": "root"}
            gui.render(module.MainViewApp, container)

            assert gui._hot_reloader._root_module_name == "__main__"
            label = container["children"][0]
            assert label["attrs"]["text"] == "Initial"

            script_path.write_text(
                dedent(MAIN_SCRIPT_TEMPLATE.format(text="Updated")).lstrip()
            )

            assert gui.reload(preserve_state=False) is True

            label = container["children"][0]
            assert label["attrs"]["text"] == "Updated"

            # The module was re-executed under a substitute name and its
            # __main__ guard did not run
            reloaded = sys.modules["main_view_script"]
            assert reloaded.GUARD_RAN is False
            assert gui._hot_reloader._root_module_name == "main_view_script"

            # A second reload should go through the substitute module
            script_path.write_text(
                dedent(MAIN_SCRIPT_TEMPLATE.format(text="Again")).lstrip()
            )
            assert gui.reload(preserve_state=False) is True
            assert container["children"][0]["attrs"]["text"] == "Again"

        finally:
            sys.modules.pop("main_view_script", None)
