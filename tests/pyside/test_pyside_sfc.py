from PySide6 import QtCore, QtWidgets

import collagraph as cg


def test_pyside_sfc_event_handlers(qapp, qtbot):
    """Test that class methods can work as event handlers in PySide."""
    from tests.data.directive_on import Buttons

    renderer = cg.PySideRenderer()
    gui = cg.Collagraph(renderer=renderer, event_loop_type=cg.EventLoopType.QT)
    container = renderer.create_element("widget")
    gui.render(cg.h(Buttons, {}), container)

    label = None
    add_button = None
    dec_button = None

    def widgets_are_found():
        nonlocal label
        nonlocal add_button
        nonlocal dec_button
        label = container.findChild(QtWidgets.QLabel)
        add_button = container.findChild(QtWidgets.QPushButton, name="add")
        dec_button = container.findChild(QtWidgets.QPushButton, name="dec")
        assert label and add_button and dec_button

    qtbot.waitUntil(widgets_are_found, timeout=500)

    assert label.text() == "0"

    qtbot.mouseClick(add_button, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: label.text() == "1", timeout=500)
    qtbot.mouseClick(dec_button, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: label.text() == "0", timeout=500)
