import pytest
from observ import reactive

pytest.importorskip("PySide6")

from PySide6 import QtCore, QtWidgets

import collagraph as cg
from collagraph.renderers.pyside_renderer import TextElementProxy


def test_create_text_element(qapp):
    renderer = cg.PySideRenderer(autoshow=False)

    proxy = renderer.create_text_element()

    assert isinstance(proxy, TextElementProxy)
    assert proxy.content == ""


def test_label_text_element(qapp):
    renderer = cg.PySideRenderer(autoshow=False)
    label = renderer.create_element("label")
    proxy = renderer.create_text_element()

    # Setting text before insert only updates the proxy
    renderer.set_element_text(proxy, "Hello")
    assert label.text() == ""

    renderer.insert(proxy, label)
    assert label.text() == "Hello"

    renderer.set_element_text(proxy, "Hello world")
    assert label.text() == "Hello world"

    renderer.remove(proxy, label)
    assert label.text() == ""


def test_button_text_element(qapp):
    renderer = cg.PySideRenderer(autoshow=False)
    button = renderer.create_element("button")
    proxy = renderer.create_text_element()

    renderer.set_element_text(proxy, "Click me")
    renderer.insert(proxy, button)

    assert button.text() == "Click me"


def test_text_element_order_with_anchor(qapp):
    renderer = cg.PySideRenderer(autoshow=False)
    label = renderer.create_element("label")

    first = renderer.create_text_element()
    second = renderer.create_text_element()
    third = renderer.create_text_element()
    renderer.set_element_text(first, "a")
    renderer.set_element_text(second, "b")
    renderer.set_element_text(third, "c")

    renderer.insert(first, label)
    renderer.insert(third, label)
    # Insert with anchor should insert before the anchor
    renderer.insert(second, label, anchor=third)

    assert label.text() == "abc"

    renderer.remove(second, label)
    assert label.text() == "ac"


def test_text_element_in_plain_widget_fails(qapp, caplog):
    renderer = cg.PySideRenderer(autoshow=False)
    widget = renderer.create_element("widget")
    proxy = renderer.create_text_element()

    # Widget does not support text elements: the error is logged
    renderer.insert(proxy, widget)

    assert "Error inserting" in caplog.text


def test_label_child_text(qtbot, parse_source):
    """Test that child text of labels and buttons updates with state."""
    Counter, _ = parse_source(
        """
        <widget>
          <label>Count: {{ count }}</label>
          <button @clicked="bump">bump</button>
        </widget>

        <script>
        import collagraph as cg

        class Counter(cg.Component):
            def init(self):
                self.state["count"] = 0

            def bump(self):
                self.state["count"] += 1
        </script>
        """
    )

    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)
    container = renderer.create_element("widget")
    gui.render(Counter, container)

    label = None
    button = None

    def widgets_are_found():
        nonlocal label
        nonlocal button
        label = container.findChild(QtWidgets.QLabel)
        button = container.findChild(QtWidgets.QPushButton)
        assert label and button

    qtbot.waitUntil(widgets_are_found, timeout=500)

    assert label.text() == "Count: 0"
    assert button.text() == "bump"

    qtbot.mouseClick(button, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: label.text() == "Count: 1", timeout=500)


def test_conditional_child_text(qtbot, parse_source):
    """Test that text elements are properly removed on unmount."""
    Example, _ = parse_source(
        """
        <label object_name="label">
          <template v-if="show">{{ message }}</template>
        </label>

        <script>
        import collagraph as cg

        class Example(cg.Component):
            pass
        </script>
        """
    )

    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)
    container = renderer.create_element("widget")
    state = reactive({"show": True, "message": "Hello"})
    gui.render(Example, container, state=state)

    label = None

    def label_is_found():
        nonlocal label
        label = container.findChild(QtWidgets.QLabel, name="label")
        assert label

    qtbot.waitUntil(label_is_found, timeout=500)

    qtbot.waitUntil(lambda: label.text() == "Hello", timeout=500)

    state["message"] = "Hi"
    qtbot.waitUntil(lambda: label.text() == "Hi", timeout=500)

    state["show"] = False
    qtbot.waitUntil(lambda: label.text() == "", timeout=500)
