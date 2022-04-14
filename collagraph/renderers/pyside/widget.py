from PySide6.QtWidgets import (
    QBoxLayout,
    QFormLayout,
    QGridLayout,
    QSpacerItem,
)

from . import camel_case, name_to_type


def insert(self, el, anchor=None):
    # Adding a widget to a widget involves getting the layout of the parent
    # and then inserting the widget into the layout. The layout might not
    # exist yet, so let's create a default QBoxLayout.
    # TODO: add support for other layouts? Maybe through special/custom attributes?
    if hasattr(el, "setParent"):
        el.setParent(self)

    layout = self.layout()
    if not layout:
        layout = QBoxLayout(QBoxLayout.Direction.TopToBottom, self)
        self.setLayout(layout)

    index = -1
    if anchor:
        index = layout.indexOf(anchor)

    if isinstance(el, QSpacerItem):
        layout.insertSpacerItem(index, el)
        return

    if hasattr(el, "grid_index"):
        layout.addWidget(el, *el.grid_index)
        return

    if hasattr(el, "form_label"):
        if hasattr(el, "form_index"):
            layout.insertRow(el.form_index, el.form_label, el)
        else:
            layout.addRow(el.form_label, el)
        return

    if hasattr(layout, "insertWidget"):
        layout.insertWidget(index, el)
    else:
        raise NotImplementedError


def remove(self, el):
    layout = self.layout()
    layout.removeWidget(el)
    el.setParent(None)


DIRECTIONS = {
    "TopToBottom": QBoxLayout.Direction.TopToBottom,
    "LeftToRight": QBoxLayout.Direction.LeftToRight,
    "RightToLeft": QBoxLayout.Direction.RightToLeft,
    "BottomToTop": QBoxLayout.Direction.BottomToTop,
}


def set_attribute(self, attr, value):
    if attr == "layout":
        if value["type"] == "Box":
            direction = DIRECTIONS[value.get("direction", "TopToBottom")]
            if isinstance(self.layout(), QBoxLayout):
                self.layout().setDirection(direction)
            else:
                self.setLayout(QBoxLayout(direction))
        elif value["type"] == "Grid":
            if isinstance(self.layout(), QGridLayout):
                pass
            else:
                self.setLayout(QGridLayout())
        elif value["type"] == "Form":
            if isinstance(self.layout(), QFormLayout):
                pass
            else:
                self.setLayout(QFormLayout())

        for key, val in value.items():
            if key == "type":
                continue
            method_name = attr_name_to_method_name(key, setter=True)
            method = getattr(self.layout(), method_name, None)
            if method:
                if key in ["column_stretch", "row_stretch"]:
                    for args in val:
                        call_method(method, args)
                else:
                    call_method(method, val)
        return
    elif attr == "grid_index":
        setattr(self, "grid_index", value)
        if parent := self.parent():
            layout = parent.layout()
            layout.addWidget(self, *value)
        return
    elif attr in ["form_label", "form_index"]:
        setattr(self, attr, value)
        if parent := self.parent():
            layout = parent.layout()
            if hasattr(self, "form_label") and hasattr(self, "form_index"):
                layout.insertRow(self.form_index, self.form_label, self)
            elif hasattr(self, "form_label"):
                layout.addRow(self.form_label, self)
        return

    method_name = attr_name_to_method_name(attr, setter=True)
    method = getattr(self, method_name, None)
    if not method:
        setattr(self, attr, value)
        return

    call_method(method, value)


def attr_name_to_method_name(name, setter=False):
    sep = "-"
    if "_" in name:
        sep = "_"

    prefix = f"set{sep}" if setter else ""
    return camel_case(f"{prefix}{name}", sep)


def call_method(method, args):
    if isinstance(args, str):
        try:
            args = name_to_type(args)
        except TypeError:
            pass
        method(args)
    else:
        try:
            method(args)
        except TypeError:
            # TODO: Maybe also call name_to_type on all values?
            method(*args)