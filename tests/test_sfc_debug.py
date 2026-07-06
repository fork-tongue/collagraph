"""Tests for the CGX_DEBUG support code paths."""

import tempfile

import collagraph.sfc
from collagraph.sfc import _write_debug_file
from collagraph.sfc.compiler import construct_ast, format_code

SIMPLE_TEMPLATE = """
<item />

<script>
import collagraph as cg

class Item(cg.Component):
    pass
</script>
"""


def test_format_code_formats_valid_code():
    assert format_code("x=1") == "x = 1\n"


def test_format_code_returns_input_when_ruff_fails():
    # Invalid syntax makes `ruff format` exit non-zero with empty
    # stdout; format_code should fall back to the unformatted input
    # instead of returning an empty string.
    broken = "def broken(:"
    assert format_code(broken) == broken


def test_load_falls_back_when_debug_source_is_broken(monkeypatch, tmp_path):
    # When the debug file somehow ends up with unparsable source,
    # loading should fall back to the original tree instead of
    # raising a SyntaxError.
    broken = "def broken(:"
    debug_file = tmp_path / "broken.py"
    debug_file.write_text(broken, encoding="utf-8")

    monkeypatch.setattr(collagraph.sfc, "DEBUG", True)
    monkeypatch.setattr(
        collagraph.sfc, "_write_debug_file", lambda tree, path: (debug_file, broken)
    )

    component, _ = collagraph.sfc.load_from_string(SIMPLE_TEMPLATE)
    assert component.__name__ == "Item"


def test_write_debug_file_avoids_mktemp(monkeypatch):
    # tempfile.mktemp is deprecated and racy (the file is created
    # after the name is picked); the debug file should be created
    # atomically instead.
    def forbidden(*args, **kwargs):
        raise AssertionError("tempfile.mktemp is deprecated and insecure")

    monkeypatch.setattr(tempfile, "mktemp", forbidden)

    tree, _ = construct_ast(path="example.cgx", template=SIMPLE_TEMPLATE)
    debug_file, source = _write_debug_file(tree, "example.cgx")

    assert debug_file is not None
    assert debug_file.name.startswith("cgx_example_")
    assert debug_file.suffix == ".py"
    assert debug_file.read_text(encoding="utf-8") == source
    debug_file.unlink()
