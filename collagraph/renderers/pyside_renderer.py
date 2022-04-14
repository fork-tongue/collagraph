from collections import defaultdict
import logging
from typing import Any, Callable

from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpacerItem,
    QSpinBox,
    QStatusBar,
    QTextEdit,
    QTreeView,
    QWidget,
)

from . import Renderer


logger = logging.getLogger(__name__)


CONFIG_MAPPING = {
    QCheckBox: {},
    QComboBox: {},
    QLabel: {},
    QLineEdit: {},
    QMainWindow: {},
    QMenuBar: {},
    QPushButton: {},
    QRadioButton: {},
    QSlider: {},
    QSpinBox: {},
    QStatusBar: {},
    QTreeView: {},
    QWidget: {},
}


TYPE_MAPPING = {
    "Button": QPushButton,
    "CheckBox": QCheckBox,
    "ComboBox": QComboBox,
    "Label": QLabel,
    "LineEdit": QLineEdit,
    "MenuBar": QMenuBar,
    "RadioButton": QRadioButton,
    "Slider": QSlider,
    "SpinBox": QSpinBox,
    "StatusBar": QStatusBar,
    "TextEdit": QTextEdit,
    "TreeView": QTreeView,
    "Widget": QWidget,
    "Window": QMainWindow,
    # Layout directions
    "TopToBottom": QBoxLayout.Direction.TopToBottom,
    "LeftToRight": QBoxLayout.Direction.LeftToRight,
    "RightToLeft": QBoxLayout.Direction.RightToLeft,
    "BottomToTop": QBoxLayout.Direction.BottomToTop,
}

LAYOUT = {
    "Box": QBoxLayout,
    "Grid": QGridLayout,
    "Form": QFormLayout,
}


DIRECTIONS = {
    "TopToBottom": QBoxLayout.Direction.TopToBottom,
    "LeftToRight": QBoxLayout.Direction.LeftToRight,
    "RightToLeft": QBoxLayout.Direction.RightToLeft,
    "BottomToTop": QBoxLayout.Direction.BottomToTop,
}


def name_to_type(name, modules=None, orig=None):
    # IDEA: use a dict as cache (or lru_cache). Might speed things up a bit?
    # Using a dict might be handy, because we can specify certain types in advance?
    if name in TYPE_MAPPING:
        return TYPE_MAPPING[name]
    if modules is None:
        modules = [QtWidgets, QtCore, QtCore.Qt]
    parts = name.split(".")
    for module in modules:
        if (element_class := getattr(module, parts[0], None)) is not None:
            if len(parts) > 1:
                return name_to_type(
                    ".".join(parts[1:]), modules=[element_class], orig=name
                )
            TYPE_MAPPING[orig or name] = element_class
            return element_class

    raise TypeError(f"Couldn't find type for name: '{name}' ({orig})")


def camel_case(event, split):
    parts = event.split(split)
    return "".join([parts[0]] + [part.capitalize() for part in parts[1:]])


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


class PySideRenderer(Renderer):
    """PySide6 renderer."""

    def create_element(self, type: str) -> Any:
        """Create an element for the given type."""
        # Make sure that an app exists before any widgets
        # are created. Otherwise we might experience a
        # hard segfault.
        QtCore.QCoreApplication.instance() or QtWidgets.QApplication()
        if type == "Spacing":
            return QSpacerItem(0, 0)
        if type == "Stretch":
            return QSpacerItem(0, 0)
        return name_to_type(type)()

    def insert(self, el: Any, parent: Any, anchor: Any = None):
        """
        Add element `el` as a child to the element `parent`.
        If an anchor is specified, it inserts `el` before the `anchor`
        element.
        """
        if isinstance(parent, QtWidgets.QDialogButtonBox) and isinstance(
            el, QPushButton
        ):
            if hasattr(el, "flag"):
                parent.addButton(getattr(QtWidgets.QDialogButtonBox, el.flag))
                return
            elif hasattr(el, "role"):
                parent.addButton(el, getattr(QtWidgets.QDialogButtonBox, el.role))
                return

        if hasattr(el, "setParent") and isinstance(parent, QtWidgets.QWidget):
            el.setParent(parent)

        if isinstance(el, QtWidgets.QMainWindow):
            # If the inserted element is a window, then there is
            # no real parent to add it to, so let's just show the
            # window element and be done with it.
            el.show()
            return

        if isinstance(parent, QtWidgets.QMainWindow):
            # If the parent is a QMainWindow, then depending on the
            # type of child, we can add the element in special ways
            if isinstance(el, QtWidgets.QDockWidget):
                # FIXME: how to specify area?
                # parent.addDockWidget(area, el)
                return
            elif isinstance(el, QtWidgets.QToolBar):
                # FIXME: how to specify area?
                # parent.addToolBar(area, el)
                parent.addToolBar(el)
                return
            else:
                # Let's assume any other given widget is just the
                # central widget of the QMainWindow
                if parent.centralWidget():
                    logger.warning("central widget of QMainWindow already set")
                parent.setCentralWidget(el)
                return

            # else:
            #     parent.addButton(el, getattr(QtWidgets.QDialogButtonBox, el.role))

        # Adding a widget to a widget involves getting the layout of the parent
        # and then inserting the widget into the layout. The layout might not
        # exist yet, so let's create a default QBoxLayout.
        # TODO: add support for other layouts? Maybe through special/custom attributes?
        layout = parent.layout()
        if not layout:
            layout = QtWidgets.QBoxLayout(
                QtWidgets.QBoxLayout.Direction.TopToBottom, parent
            )
            parent.setLayout(layout)

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

    def remove(self, el: Any, parent: Any):
        """Remove the element `el` from the children of the element `parent`."""
        layout = parent.layout()
        layout.removeWidget(el)
        el.setParent(None)

    def set_attribute(self, el: Any, attr: str, value: Any):
        """Set the attribute `attr` of the element `el` to the value `value`."""
        # Support a custom attribute 'layout_direction' so that we can
        # set the layout direction of the layout of the given element
        if attr == "layout":
            if value["type"] == "Box":
                direction = DIRECTIONS[value.get("direction", "TopToBottom")]
                if isinstance(el.layout(), QBoxLayout):
                    el.layout().setDirection(direction)
                else:
                    el.setLayout(QBoxLayout(direction))
            elif value["type"] == "Grid":
                if isinstance(el.layout(), QGridLayout):
                    pass
                else:
                    el.setLayout(QGridLayout())
            elif value["type"] == "Form":
                if isinstance(el.layout(), QFormLayout):
                    pass
                else:
                    el.setLayout(QFormLayout())

            for key, val in value.items():
                if key == "type":
                    continue
                method_name = attr_name_to_method_name(key, setter=True)
                method = getattr(el.layout(), method_name, None)
                if method:
                    if key in ["column_stretch", "row_stretch"]:
                        for args in val:
                            call_method(method, args)
                    else:
                        call_method(method, val)
            return

        if attr == "grid_index":
            setattr(el, "grid_index", value)
            if parent := el.parent():
                layout = parent.layout()
                layout.addWidget(el, *value)
            return

        if attr in ["form_label", "form_index"]:
            setattr(el, attr, value)
            if parent := el.parent():
                layout = parent.layout()
                if hasattr(el, "form_label") and hasattr(el, "form_index"):
                    layout.insertRow(el.form_index, el.form_label, el)
                elif hasattr(el, "form_label"):
                    layout.addRow(el.form_label, el)
            return

        method_name = attr_name_to_method_name(attr, setter=True)
        method = getattr(el, method_name, None)
        if not method:
            setattr(el, attr, value)
            return

        call_method(method, value)

    def remove_attribute(self, el: Any, attr: str, value: Any):
        """Remove the attribute `attr` from the element `el`."""
        # TODO: what does it mean to remove an attribute? How to define default values?
        raise NotImplementedError

    def add_event_listener(self, el: Any, event_type: str, value: Callable):
        """Add event listener for `event_type` to the element `el`."""
        if not value:
            return

        event_type = camel_case(event_type, "_")

        # Add a slots attribute to hold all the generated slots, keyed on event_type
        if not hasattr(el, "slots"):
            el.slots = defaultdict(set)

        # Create a slot with the given value
        # Note that the slot apparently does not need arguments to specify the type
        # or amount of arguments the enclosed callback needs. If the callback has
        # arguments, then those will be set to the parameter(s) of the signal when
        # it is emitted.
        slot = QtCore.Slot()(value)
        el.slots[event_type].add(slot)

        # Try and get the signal from the object
        signal = getattr(el, event_type, None)
        if signal:
            signal.connect(slot)

    def remove_event_listener(self, el: Any, event_type: str, value: Callable):
        """Remove event listener for `event_type` to the element `el`."""
        if not hasattr(el, "slots"):
            return

        signal = getattr(el, event_type, None)
        if not signal:
            return

        for slot in el.slots[event_type]:
            # Slot can be compared to its value
            if slot == value:
                signal.disconnect(slot)
                el.slots[event_type].remove(slot)
                break
