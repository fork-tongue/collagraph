import logging

from PySide6.QtWidgets import (
    QBoxLayout,
    QFormLayout,
    QGridLayout,
    QLayout,
    QStackedLayout,
    QWidget,
)

from .qobject import set_attribute as qobject_set_attribute
from .. import attr_name_to_method_name, call_method
from ...pyside_renderer import LAYOUT_MAPPING, PySideRenderer

logger = logging.getLogger(__name__)

DIRECTIONS = {
    "TopToBottom": QBoxLayout.Direction.TopToBottom,
    "LeftToRight": QBoxLayout.Direction.LeftToRight,
    "RightToLeft": QBoxLayout.Direction.RightToLeft,
    "BottomToTop": QBoxLayout.Direction.BottomToTop,
}


PySideRenderer.register_layout("box", QBoxLayout)
PySideRenderer.register_layout("form", QFormLayout)
PySideRenderer.register_layout("grid", QGridLayout)
PySideRenderer.register_layout("stacked", QStackedLayout)


@PySideRenderer.register_insert(QLayout)
def layout_insert(self, el, anchor=None):
    self.addWidget(el)


@PySideRenderer.register_insert(QBoxLayout, QStackedLayout)
def box_layout_insert(self, el, anchor=None):
    index = -1
    if anchor is not None:
        index = self.indexOf(anchor)

    self.insertWidget(index, el)


@PySideRenderer.register_insert(QFormLayout)
def form_insert(self, el, anchor=None):
    if hasattr(el, "form_index"):
        self.insertRow(el.form_index, el.form_label, el)
    else:
        self.addRow(el.form_label, el)


@PySideRenderer.register_insert(QGridLayout)
def grid_insert(self, el, anchor=None):
    self.addWidget(el, *el.grid_index)


@PySideRenderer.register_insert(QWidget)
def insert(self, el, anchor=None):
    el.setParent(self)

    # Adding a widget (el) to a widget (self) involves getting the layout
    # of the parent (self) and then inserting the widget into the layout.
    # The layout might not exist yet, so let's create a default QBoxLayout.
    layout = self.layout()
    if not layout:
        layout = PySideRenderer.create_object("box")
        self.setLayout(layout)

    layout.insert(el, anchor=anchor)


@PySideRenderer.register_remove(QWidget)
def remove(self, el):
    layout = self.layout()
    if hasattr(layout, "remove"):
        layout.remove(el)
    else:
        # Some layouts in the hierarchy are not wrapped
        # because PySide creates them internally, hence
        # the need to have a fallback
        remove_layout(layout, el)


@PySideRenderer.register_remove(QLayout)
def remove_layout(self, el):
    self.removeWidget(el)
    el.setParent(None)


@PySideRenderer.register_remove(QFormLayout)
def remove_form(self, el):
    # Layout also deletes 'el' so no need to unset parent
    self.removeRow(el)


@PySideRenderer.register_set_attr(QLayout)
def set_layout_attribute(self, attr, value):
    if attr == "type":
        return
    method_name = attr_name_to_method_name(attr, setter=True)
    if method := getattr(self.layout(), method_name, None):
        if attr in {"direction"}:
            arg = DIRECTIONS[value]
            call_method(method, arg)
        elif attr in {"column_stretch", "row_stretch"}:
            for args in value:
                call_method(method, args)
        else:
            call_method(method, value)


@PySideRenderer.register_set_attr(QWidget)
def set_attribute(self, attr, value):
    if attr == "layout":
        if layout_type := LAYOUT_MAPPING.get(value["type"].lower()):
            layout = self.layout()
            if isinstance(layout, layout_type):
                pass
            else:
                if layout:
                    QWidget().setLayout(layout)
                layout = PySideRenderer.create_object(value["type"].lower())
                self.setLayout(layout)

            for key, val in value.items():
                layout.set_attribute(key, val)
        else:
            raise RuntimeError(f"No layout registered for type: {value['type']}")

        return
    # FIXME: register
    elif attr == "grid_index":
        self.grid_index = value
        if parent := self.parent():
            layout = parent.layout()
            layout.addWidget(self, *value)
        return
    # FIXME: register
    elif attr in {"form_label", "form_index"}:
        setattr(self, attr, value)
        if parent := self.parent():
            layout = parent.layout()
            if hasattr(self, "form_label") and hasattr(self, "form_index"):
                layout.insertRow(self.form_index, self.form_label, self)
            elif hasattr(self, "form_label"):
                layout.addRow(self.form_label, self)
        return
    elif attr == "size":
        self.resize(*value)
        return

    qobject_set_attribute(self, attr, value)
