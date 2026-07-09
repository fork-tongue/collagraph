"""Tests for running Python view components through the CLI."""

import argparse
import sys
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from collagraph.__main__ import existing_component_file, load_component_class, run

SINGLE_COMPONENT = """
import collagraph as cg
from collagraph import h


class Single(cg.Component):
    def view(self):
        h.label(text="single")
"""

MULTIPLE_COMPONENTS = """
import collagraph as cg
from collagraph import h


class Child(cg.Component):
    def view(self):
        h.label(text="child")


class App(cg.Component):
    def view(self):
        with h.widget():
            h(Child)
"""


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        inserted = []
        yield Path(tmpdir), inserted
        # load_component_class inserts the module directory into sys.path
        resolved = str(Path(tmpdir).resolve())
        if resolved in sys.path:
            sys.path.remove(resolved)
        for name in inserted:
            sys.modules.pop(name, None)


def test_component_argument_parsing(tmp_path):
    py_path = tmp_path / "some_component.py"
    py_path.write_text("")

    assert existing_component_file(str(py_path)) == (py_path, None)
    assert existing_component_file(f"{py_path}:MyClass") == (py_path, "MyClass")

    with pytest.raises(argparse.ArgumentTypeError, match="does not exist"):
        existing_component_file(str(tmp_path / "missing.py"))

    txt_path = tmp_path / "not_a_component.txt"
    txt_path.write_text("")
    with pytest.raises(argparse.ArgumentTypeError, match="not a collagraph component"):
        existing_component_file(str(txt_path))

    cgx_path = tmp_path / "some_component.cgx"
    cgx_path.write_text("")
    with pytest.raises(argparse.ArgumentTypeError, match=r"only supported for \.py"):
        existing_component_file(f"{cgx_path}:MyClass")


def test_load_single_view_component(temp_dir):
    tmpdir, inserted = temp_dir
    path = tmpdir / "cli_single_view.py"
    path.write_text(dedent(SINGLE_COMPONENT).lstrip())
    inserted.append("cli_single_view")

    component_class = load_component_class(path)
    assert component_class.__name__ == "Single"


def test_load_selected_view_component(temp_dir):
    tmpdir, inserted = temp_dir
    path = tmpdir / "cli_multi_view.py"
    path.write_text(dedent(MULTIPLE_COMPONENTS).lstrip())
    inserted.append("cli_multi_view")

    component_class = load_component_class(path, "App")
    assert component_class.__name__ == "App"

    with pytest.raises(SystemExit, match="is not a Component subclass"):
        load_component_class(path, "Missing")


def test_load_multiple_view_components_requires_selection(temp_dir):
    tmpdir, inserted = temp_dir
    path = tmpdir / "cli_ambiguous_view.py"
    path.write_text(dedent(MULTIPLE_COMPONENTS).lstrip())
    inserted.append("cli_ambiguous_view")

    with pytest.raises(SystemExit, match=r"Multiple view components.*:App"):
        load_component_class(path)


def test_load_explicit_component_class(temp_dir):
    """A module can mark its root component with __component_class."""
    tmpdir, inserted = temp_dir
    path = tmpdir / "cli_explicit_view.py"
    path.write_text(
        dedent(MULTIPLE_COMPONENTS).lstrip() + "\n__component_class = Child\n"
    )
    inserted.append("cli_explicit_view")

    component_class = load_component_class(path)
    assert component_class.__name__ == "Child"


def test_load_no_view_component(temp_dir):
    tmpdir, inserted = temp_dir
    path = tmpdir / "cli_no_view.py"
    path.write_text("x = 1\n")
    inserted.append("cli_no_view")

    with pytest.raises(SystemExit, match="No view component found"):
        load_component_class(path)


def test_show_code_rejects_py_files(monkeypatch, tmp_path, capsys):
    path = tmp_path / "cli_show_code_view.py"
    path.write_text(dedent(SINGLE_COMPONENT).lstrip())
    monkeypatch.setattr(sys, "argv", ["collagraph", "--show-code", str(path)])

    with pytest.raises(SystemExit):
        run()

    captured = capsys.readouterr()
    assert "--show-code is only supported for .cgx files" in captured.err
