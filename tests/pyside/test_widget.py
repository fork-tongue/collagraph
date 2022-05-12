import collagraph as cg


def test_widget_size(qapp, qtbot):
    renderer = cg.PySideRenderer()
    widget = renderer.create_element("widget")
    renderer.set_attribute(widget, "size", (600, 400))

    assert widget.size().width() == 600
    assert widget.size().height() == 400
