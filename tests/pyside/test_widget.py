import collagraph as cg


def test_widget_size():
    renderer = cg.PySideRenderer()
    widget = renderer.create_element("widget")
    renderer.set_attribute(widget, "size", (600, 400))

    assert widget.size().width() == 600
    assert widget.size().height() == 400


def test_widget_close():
    closed = False

    def close(event):
        nonlocal closed
        closed = True

    renderer = cg.PySideRenderer()
    widget = renderer.create_element("widget")
    renderer.add_event_listener(widget, "close", close)

    widget.close()

    assert closed is True
