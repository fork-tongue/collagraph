import pytest
from observ import reactive

pytest.importorskip("PySide6")

from PySide6 import QtWidgets

import collagraph as cg


def test_hbox_vbox_layouts(qtbot, parse_source):
    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    Element, _ = parse_source(
        """
        <widget object-name="root" :layout="{'type': 'vbox'}">
          <widget
            object-name="inner"
            :layout="{'type': 'hbox', 'direction': 'RightToLeft'}"
          >
            <label text="A" />
            <label text="B" />
          </widget>
        </widget>

        <script>
        import collagraph as cg

        class Element(cg.Component):
            pass
        </script>
        """
    )

    container = renderer.create_element("Widget")
    gui.render(Element, container)

    def check():
        root = container.findChild(QtWidgets.QWidget, name="root")
        assert root
        assert isinstance(root.layout(), QtWidgets.QVBoxLayout)

        inner = root.findChild(QtWidgets.QWidget, name="inner")
        assert inner
        assert isinstance(inner.layout(), QtWidgets.QHBoxLayout)
        assert inner.layout().direction() == QtWidgets.QBoxLayout.Direction.RightToLeft

    qtbot.waitUntil(check, timeout=500)


def test_box_direction_aliases_horizontal_vertical(qtbot, parse_source):
    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    Element, _ = parse_source(
        """
        <widget object-name="root" :layout="{'type': 'vbox'}">
          <widget
            object-name="h"
            :layout="{'type': 'box', 'direction': 'horizontal'}"
          />
          <widget
            object-name="v"
            :layout="{'type': 'box', 'direction': 'vertical'}"
          />
        </widget>

        <script>
        import collagraph as cg

        class Element(cg.Component):
            pass
        </script>
        """
    )

    container = renderer.create_element("Widget")
    gui.render(Element, container)

    def check():
        root = container.findChild(QtWidgets.QWidget, name="root")
        assert root

        h = root.findChild(QtWidgets.QWidget, name="h")
        assert h
        assert isinstance(h.layout(), QtWidgets.QBoxLayout)
        assert h.layout().direction() == QtWidgets.QBoxLayout.Direction.LeftToRight

        v = root.findChild(QtWidgets.QWidget, name="v")
        assert v
        assert isinstance(v.layout(), QtWidgets.QBoxLayout)
        assert v.layout().direction() == QtWidgets.QBoxLayout.Direction.TopToBottom

    qtbot.waitUntil(check, timeout=500)


def test_grid_layout_stretch_and_late_grid_index(qtbot, parse_source):
    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    Element, _ = parse_source(
        """
        <widget object-name="grid" :layout="grid_layout">
          <label object-name="child" text="X" v-bind="child_bind" />
        </widget>

        <script>
        import collagraph as cg

        class Element(cg.Component):
            pass
        </script>
        """
    )

    state = reactive(
        {
            "grid_layout": {
                "type": "grid",
                "column_stretch": [(0, 1), (1, 2)],
                "row_stretch": [(0, 3)],
            },
            "child_bind": {},
        }
    )

    container = renderer.create_element("Widget")
    gui.render(Element, container, state=state)

    def check_layout():
        grid = container.findChild(QtWidgets.QWidget, name="grid")
        assert grid
        layout = grid.layout()
        assert isinstance(layout, QtWidgets.QGridLayout)
        assert layout.columnStretch(0) == 1
        assert layout.columnStretch(1) == 2
        assert layout.rowStretch(0) == 3

    qtbot.waitUntil(check_layout, timeout=500)

    # Set grid_index after mount; this should add the widget
    # to the grid layout at that position
    state["child_bind"] = {"grid_index": (0, 0)}

    def check_child_positioned():
        grid = container.findChild(QtWidgets.QWidget, name="grid")
        child = container.findChild(QtWidgets.QLabel, name="child")
        assert grid and child
        item = grid.layout().itemAtPosition(0, 0)
        assert item is not None
        assert item.widget() is child

    qtbot.waitUntil(check_child_positioned, timeout=500)


def test_form_label_update_and_reorder(qtbot, parse_source):
    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    Element, _ = parse_source(
        """
        <widget object-name="form" :layout="{'type': 'form'}">
          <lineedit object-name="f1" :form_index="f1_index" :form_label="f1_label" />
          <lineedit object-name="f2" :form_index="f2_index" :form_label="f2_label" />
        </widget>

        <script>
        import collagraph as cg

        class Element(cg.Component):
            pass
        </script>
        """
    )

    state = reactive(
        {
            "f1_index": 0,
            "f1_label": "First",
            "f2_index": 1,
            "f2_label": "Second",
        }
    )

    container = renderer.create_element("Widget")
    gui.render(Element, container, state=state)

    form = None
    layout = None
    original_label_widget = None

    def capture_original_label_widget():
        nonlocal form, layout, original_label_widget
        form = container.findChild(QtWidgets.QWidget, name="form")
        assert form
        layout = form.layout()
        assert isinstance(layout, QtWidgets.QFormLayout)
        original_label_widget = layout.itemAt(
            0, QtWidgets.QFormLayout.LabelRole
        ).widget()
        assert isinstance(original_label_widget, QtWidgets.QLabel)
        assert original_label_widget.text() == "First"

    qtbot.waitUntil(capture_original_label_widget, timeout=500)

    # Move f1 after f2 and update the label; set_form_index should
    # preserve the existing label widget.
    state["f1_index"] = 1
    state["f1_label"] = "Updated"

    def check_reordered_and_updated():
        assert (
            layout.itemAt(0, QtWidgets.QFormLayout.FieldRole).widget().objectName()
            == "f2"
        )
        assert (
            layout.itemAt(1, QtWidgets.QFormLayout.FieldRole).widget().objectName()
            == "f1"
        )
        label_widget = layout.itemAt(1, QtWidgets.QFormLayout.LabelRole).widget()
        assert label_widget is original_label_widget
        assert label_widget.text() == "Updated"

    qtbot.waitUntil(check_reordered_and_updated, timeout=500)


def test_remove_from_form_layout_removes_label_widget(qtbot, parse_source):
    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    Element, _ = parse_source(
        """
        <widget object-name="form" :layout="{'type': 'form'}">
          <lineedit
            v-if="show"
            object-name="field"
            :form_index="0"
            :form_label="'Hello'"
          />
        </widget>

        <script>
        import collagraph as cg

        class Element(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"show": True})

    container = renderer.create_element("Widget")
    gui.render(Element, container, state=state)

    form = None
    label_widget = None

    def capture_label_widget():
        nonlocal form, label_widget
        form = container.findChild(QtWidgets.QWidget, name="form")
        assert form
        layout = form.layout()
        assert isinstance(layout, QtWidgets.QFormLayout)
        label_widget = layout.itemAt(0, QtWidgets.QFormLayout.LabelRole).widget()
        assert isinstance(label_widget, QtWidgets.QLabel)

    qtbot.waitUntil(capture_label_widget, timeout=500)

    state["show"] = False

    def check_removed():
        assert form.findChild(QtWidgets.QLineEdit, name="field") is None
        assert label_widget.parent() is None
        assert form.layout().rowCount() == 0

    qtbot.waitUntil(check_removed, timeout=500)
