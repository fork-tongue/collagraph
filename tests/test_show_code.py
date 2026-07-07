"""Tests for the --show-code CLI feature."""

import sys
from pathlib import Path

from collagraph.__main__ import run
from collagraph.sfc.compiler import generate_source

EXAMPLE_CGX = Path(__file__).parent / "data" / "example.cgx"


def test_generate_source():
    source = generate_source(EXAMPLE_CGX)

    assert "class Example(cg.Component):" in source
    assert "def render(self, renderer):" in source
    # The generated source should be valid Python
    compile(source, "example.py", mode="exec")


def test_cli_show_code(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["collagraph", "--show-code", str(EXAMPLE_CGX)])

    run()

    captured = capsys.readouterr()
    assert "example.cgx" in captured.out
    assert "class Example" in captured.out
    assert "def render" in captured.out
