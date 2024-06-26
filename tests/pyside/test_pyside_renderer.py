import gc
from weakref import ref

import pytest
from observ import reactive

pytest.importorskip("PySide6")

from PySide6 import QtCore, QtWidgets

import collagraph as cg


def test_simple_widget(qtbot):
    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    element = cg.h("Widget", {"layout": {"type": "Box", "direction": "RightToLeft"}})
    container = renderer.create_element("Widget")
    gui.render(element, container)

    def check_layout():
        # Test the default direction of box layout
        assert (
            container.layout()
            and container.layout().direction()
            == QtWidgets.QBoxLayout.Direction.TopToBottom
        )
        el = container.findChild(QtWidgets.QWidget)
        # Test the custom direction for the widget
        assert el.layout().direction() == QtWidgets.QBoxLayout.Direction.RightToLeft

    qtbot.waitUntil(check_layout, timeout=500)


def test_label(qtbot):
    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    element = cg.h(
        "Widget", {"layout": {"type": "Box"}}, cg.h("Label", {"text": "Foo"})
    )
    container = renderer.create_element("Window")
    gui.render(element, container)

    def check_label():
        label = container.findChild(QtWidgets.QLabel)
        assert label and label.text() == "Foo"

    qtbot.waitUntil(check_label, timeout=500)


def test_register_custom_widget_subclass():
    # Register the class CustomWidget as element Foo
    @cg.PySideRenderer.register_element("Foo")
    class CustomWidget(QtWidgets.QWidget):
        pass

    class NonWidget:
        pass

    renderer = cg.PySideRenderer(autoshow=False)

    with pytest.warns(UserWarning):
        # It's also possible to register the element with the following line
        # However, there is already an element registered for Foo, so
        # a warning will be issued
        renderer.register_element("Foo", CustomWidget)

    foo = renderer.create_element("Foo")
    assert isinstance(foo, CustomWidget)

    with pytest.raises(TypeError):
        renderer.register_element("Bar", NonWidget)

    with pytest.raises(TypeError):
        renderer.create_element("Bar")


def test_register_custom_layout_subclass():
    class HorizontalLayout(QtWidgets.QBoxLayout):
        def __init__(self, parent=None):
            super().__init__(QtWidgets.QBoxLayout.Direction.LeftToRight, parent)

    renderer = cg.PySideRenderer(autoshow=False)
    renderer.register_layout("horizontal", HorizontalLayout)

    widget = renderer.create_element("widget")
    renderer.set_attribute(widget, "layout", {"type": "Horizontal"})

    assert isinstance(widget.layout(), HorizontalLayout)


def test_widget_add_remove(qtbot):
    def Example(props):
        children = []
        if props["label"]:
            children.append(cg.h("Label", {}))
        return cg.h("Widget", {}, *children)

    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    state = reactive({"label": True})
    element = cg.h(Example, state)
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
    renderer = cg.PySideRenderer(autoshow=False)

    # QAbstractAnimation is a type that we'll likely not
    # support so is a good candidate for checking for
    # NotImplementedError
    item = renderer.create_element("QAbstractAnimation")
    assert isinstance(item, QtCore.QAbstractAnimation)

    with pytest.raises(NotImplementedError):
        item.insert(None)


def test_removing_attribute_not_supported():
    renderer = cg.PySideRenderer(autoshow=False)

    rect = QtCore.QRect(0, 0, 20, 20)

    widget = renderer.create_element("widget")
    # This results in a custom attribute being set on widget
    renderer.set_attribute(widget, "foo", False)
    # This results in a call to `setGeometry`
    renderer.set_attribute(widget, "geometry", rect)

    assert hasattr(widget, "foo")
    assert hasattr(widget, "geometry")
    # Check that the geometry has been set through `setGeometry`
    assert callable(widget.geometry)
    assert widget.geometry != rect
    assert widget.geometry() == rect

    # Try and remove a non-existing property
    with pytest.raises(NotImplementedError):
        renderer.remove_attribute(widget, "bar", "bar")

    renderer.remove_attribute(widget, "foo", False)
    assert not hasattr(widget, "foo")

    # Removing Qt properties *is* actually supported now
    renderer.remove_attribute(widget, "geometry", rect)


def test_pyside_event_listeners(qtbot):
    clicked = 0

    def Example(props):
        children = []
        if props["label"] is True:
            children.append(cg.h("Label", {"text": "Foo"}))
            children.append(cg.h("Button", {"on_clicked": button_clicked}))
        else:
            children.append(cg.h("Label", {"text": "Bar"}))
            children.append(cg.h("Button"))

        return cg.h("Widget", {}, *children)

    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    container = renderer.create_element("Widget")
    state = reactive({"label": True})

    def button_clicked():
        nonlocal clicked
        clicked += 1
        state["label"] = False

    element = cg.h(Example, state)

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
        assert label and label.text() == "Bar"
        button = container.findChild(QtWidgets.QPushButton)

    qtbot.waitUntil(check_wait, timeout=500)

    qtbot.mouseClick(button, QtCore.Qt.LeftButton)
    # The callback should have been removed at this point
    assert clicked == 1


def test_cleanup_collagraph_instance(qapp):
    element = cg.h("widget")
    gui = cg.Collagraph(renderer=cg.PySideRenderer(autoshow=False))
    gui.render(element, qapp)

    # Create a weak ref to gui
    gui_ref = ref(gui)
    # Set the collagraph instance to None
    gui = None
    # Give Pyside/Qt a chance to cleanup
    qapp.processEvents()
    # Force garbage collection
    gc.collect()

    # Now we expect the weak ref to be empty
    assert not gui_ref()


def test_is_new_no_type_error(qapp):
    # Comparing a QtCore.Qt.ItemFlags with None results in a TypeError
    # This can happen during reconciliation so let's make sure we test for that
    state = reactive({"flags": QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable})
    element = cg.h("widget", state)
    gui = cg.Collagraph(
        renderer=cg.PySideRenderer(autoshow=False),
        event_loop_type=cg.EventLoopType.SYNC,
    )
    gui.render(element, qapp)

    # Resetting the flags property to None should also not result in a TypeError
    state["flags"] = None
