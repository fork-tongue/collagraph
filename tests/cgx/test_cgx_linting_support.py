import ast
from pathlib import Path

from collagraph.cgx import cgx

DATA_PATH = Path(__file__).parent.parent / "data"


def test_cgx_construct_ast():
    tree, name = cgx.construct_ast(DATA_PATH / "simple.cgx")

    assert name == "Simple"
    assert isinstance(tree, ast.Module)
    import_collagraph, class_def = tree.body
    assert class_def.name == "Simple"
