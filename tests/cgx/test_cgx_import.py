import pytest

import collagraph as cg


def test_cgx_import():
    from tests.data.simple import Simple

    assert issubclass(Simple, cg.Component)

    simple = Simple({})
    node = simple.render()

    assert node.type == "label"
    assert node.props["text"] == "Simple"


def test_cgx_multiple_classes():
    with pytest.raises(ValueError):
        import tests.data.multiple_classes_wrong_order  # noqa: F401

    import tests.data.multiple_classes_right_order  # noqa: F401


def test_cgx_no_component_class():
    with pytest.raises(ValueError):
        import tests.data.no_component_class  # noqa: F401


def test_cgx_multiple_root_elements():
    with pytest.raises(ValueError):
        import tests.data.multiple_root_elements  # noqa: F401
