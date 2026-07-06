"""Tests for the CGX_DEBUG support code paths."""

from collagraph.sfc.compiler import format_code


def test_format_code_formats_valid_code():
    assert format_code("x=1") == "x = 1\n"


def test_format_code_returns_input_when_ruff_fails():
    # Invalid syntax makes `ruff format` exit non-zero with empty
    # stdout; format_code should fall back to the unformatted input
    # instead of returning an empty string.
    broken = "def broken(:"
    assert format_code(broken) == broken
