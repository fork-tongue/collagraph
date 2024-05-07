import pytest

import collagraph as cg


def test_cgx_import():
    from tests.data.simple import Simple

    assert issubclass(Simple, cg.Component)

    gui = cg.Collagraph(
        renderer=cg.DictRenderer(),
        event_loop_type=cg.EventLoopType.SYNC,
    )
    target = {"type": "root"}

    gui.render(Simple, target)

    assert target["children"][0] == {"type": "label", "attrs": {"text": "Simple"}}


def test_cgx_multiple_classes():
    with pytest.raises(ValueError):
        import tests.data.multiple_classes_wrong_order

    import tests.data.multiple_classes_right_order  # noqa: F401


def test_cgx_no_component_class():
    with pytest.raises(ValueError):
        import tests.data.no_component_class  # noqa: F401
