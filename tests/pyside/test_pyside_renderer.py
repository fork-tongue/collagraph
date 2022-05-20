from observ import reactive
import pytest

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    pytest.skip(
        "skip test for PySide6 renderer when not available", allow_module_level=True
    )

from collagraph import Collagraph, create_element as h, EventLoopType
from collagraph.renderers import PySideRenderer


def test_simple_widget():
    renderer = PySideRenderer(autoshow=False)
    gui = Collagraph(renderer=renderer, event_loop_type=EventLoopType.SYNC)

    element = h("Widget", {"layout": {"type": "Box", "direction": "RightToLeft"}})
    container = renderer.create_element("Widget")
    gui.render(element, container)

    # Test the default direction of box layout
    assert container.layout().direction() == QtWidgets.QBoxLayout.Direction.TopToBottom
    el = container.findChild(QtWidgets.QWidget)
    # Test the custom direction for the widget
    assert el.layout().direction() == QtWidgets.QBoxLayout.Direction.RightToLeft


def test_label(qtbot):
    renderer = PySideRenderer(autoshow=False)
    gui = Collagraph(renderer=renderer, event_loop_type=EventLoopType.QT)

    element = h("Widget", {"layout": {"type": "Box"}}, h("Label", {"text": "Foo"}))
    container = renderer.create_element("Window")
    gui.render(element, container)

    def check_label():
        label = container.findChild(QtWidgets.QLabel)
        assert label
        assert label.text() == "Foo"

    qtbot.waitUntil(check_label, timeout=500)


def test_register_custom_type():
    class CustomWidget(QtWidgets.QWidget):
        pass

    renderer = PySideRenderer(autoshow=False)
    renderer.register("Foo", CustomWidget)

    foo = renderer.create_element("Foo")
    assert isinstance(foo, CustomWidget)

    class NonWidget:
        pass

    with pytest.raises(TypeError):
        renderer.register("Bar", NonWidget)

    with pytest.raises(TypeError):
        renderer.create_element("Bar")


def test_widget_add_remove(qtbot):
    def Example(props):
        children = []
        if props["label"]:
            children.append(h("Label", {}))
        return h("Widget", {}, *children)

    renderer = PySideRenderer(autoshow=False)
    gui = Collagraph(renderer=renderer, event_loop_type=EventLoopType.QT)

    state = reactive({"label": True})
    element = h(Example, state)
    container = renderer.create_element("Widget")
    gui.render(element, container)

    def check_label_is_added():
        assert container.findChild(QtWidgets.QLabel)

    qtbot.waitUntil(check_label_is_added, timeout=500)

    state["label"] = False

    def check_label_is_removed():
        assert not container.findChild(QtWidgets.QLabel)

    qtbot.waitUntil(check_label_is_removed, timeout=500)


def test_not_implemented():
    renderer = PySideRenderer(autoshow=False)

    # QAbstractAnimation is a type that we'll likely not
    # support so is a good candidate for checking for
    # NotImplementedError
    item = renderer.create_element("QAbstractAnimation")
    assert isinstance(item, QtCore.QAbstractAnimation)

    with pytest.raises(NotImplementedError):
        item.insert(None)


def test_removing_attribute_not_supported():
    renderer = PySideRenderer(autoshow=False)
    with pytest.raises(NotImplementedError):
        renderer.remove_attribute(None, None, None)


def test_pyside_event_listeners(qapp, qtbot):
    clicked = 0

    def Example(props):
        children = []
        if props["label"] is True:
            children.append(h("Label", {"text": "Foo"}))
            children.append(h("Button", {"on_clicked": button_clicked}))
        else:
            children.append(h("Label", {"text": "Bar"}))
            children.append(h("Button"))

        return h("Widget", {}, *children)

    renderer = PySideRenderer(autoshow=False)
    gui = Collagraph(renderer=renderer, event_loop_type=EventLoopType.QT)

    container = renderer.create_element("Widget")
    state = reactive({"label": True})

    def button_clicked():
        nonlocal clicked
        clicked += 1
        state["label"] = False

    # Define Qt structure and map state to the structure
    element = h(Example, state)

    # Pass in the app as a container. Can actually be any truthy object
    gui.render(element, container)

    button = None

    def check_button():
        nonlocal button
        button = container.findChild(QtWidgets.QPushButton)
        assert button

    qtbot.waitUntil(check_button, timeout=500)

    qtbot.mouseClick(button, QtCore.Qt.LeftButton)
    assert clicked == 1

    def check_wait():
        nonlocal button
        label = container.findChild(QtWidgets.QLabel)
        assert label.text() == "Bar"
        button = container.findChild(QtWidgets.QPushButton)

    qtbot.waitUntil(check_wait, timeout=500)

    qtbot.mouseClick(button, QtCore.Qt.LeftButton)
    # The callback should have been removed at this point
    assert clicked == 1
