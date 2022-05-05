import collagraph as cg


def test_cgx_import():
    from tests.data.simple import Simple

    assert issubclass(Simple, cg.Component)

    simple = Simple({})
    node = simple.render()

    assert node.type == "label"
    assert node.props["text"] == "Simple"
