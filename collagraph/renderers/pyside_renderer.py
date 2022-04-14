from collections import defaultdict
import logging
from typing import Any, Callable

from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
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


def not_implemented(self, *args, **kwargs):
    raise NotImplementedError(type(self).__name__)


def set_attr(self, attr, value):
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

    if attr == "grid_index":
        setattr(self, "grid_index", value)
        if parent := self.parent():
            layout = parent.layout()
            layout.addWidget(self, *value)
        return

    if attr in ["form_label", "form_index"]:
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


def remove_from_widget(self, other):
    layout = self.layout()
    layout.removeWidget(other)
    other.setParent(None)


def add_to_window(self, other, anchor=None):
    # If the parent is a QMainWindow, then depending on the
    # type of child, we can add the element in special ways
    if isinstance(other, QtWidgets.QDockWidget):
        # FIXME: how to specify area?
        # parent.addDockWidget(area, other)
        pass
    elif isinstance(other, QtWidgets.QToolBar):
        # FIXME: how to specify area?
        # parent.addToolBar(area, other)
        self.addToolBar(other)
    else:
        # Let's assume any other given widget is just the
        # central widget of the QMainWindow
        if self.centralWidget():
            logger.warning("central widget of QMainWindow already set")
        self.setCentralWidget(other)
        other.setParent(self)


def add_to_widget(self, other, anchor=None):
    # Adding a widget to a widget involves getting the layout of the parent
    # and then inserting the widget into the layout. The layout might not
    # exist yet, so let's create a default QBoxLayout.
    # TODO: add support for other layouts? Maybe through special/custom attributes?
    if hasattr(other, "setParent"):
        other.setParent(self)
    layout = self.layout()
    if not layout:
        layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.TopToBottom, self)
        self.setLayout(layout)

    index = -1
    if anchor:
        index = layout.indexOf(anchor)

    if isinstance(other, QSpacerItem):
        layout.insertSpacerItem(index, other)
        return

    if hasattr(other, "grid_index"):
        layout.addWidget(other, *other.grid_index)
        return

    if hasattr(other, "form_label"):
        if hasattr(other, "form_index"):
            layout.insertRow(other.form_index, other.form_label, other)
        else:
            layout.addRow(other.form_label, other)
        return

    if hasattr(layout, "insertWidget"):
        layout.insertWidget(index, other)
    else:
        raise NotImplementedError


def add_to_dialog_button_box(self, other, anchor=None):
    if hasattr(other, "flag"):
        self.addButton(getattr(QtWidgets.QDialogButtonBox, other.flag))
        return
    elif hasattr(other, "role"):
        self.addButton(other, getattr(QtWidgets.QDialogButtonBox, other.role))
        return
    raise NotImplementedError


INSERT_MAPPING = {
    "Widget": add_to_widget,
    "GroupBox": add_to_widget,
    "Window": add_to_window,
    "DialogButtonBox": add_to_dialog_button_box,
}
REMOVE_MAPPING = {
    "Widget": remove_from_widget,
}
SET_ATTR_MAPPING = {
    "Window": set_attr,
    "Widget": set_attr,
}

# Dicts with types to their custom implementations
# * insertChild -> insert
# * patchProp -> set_attribute
# * removeChild -> remove


# Add examples for:
# * QTabWidget
# * QTreeView
# * QTableView
# * QListView
# * slider / progress / float all connected


TYPE_MAPPING = {
    "Button": QPushButton,
    "CheckBox": QCheckBox,
    "ComboBox": QComboBox,
    "Label": QLabel,
    "LineEdit": QLineEdit,
    "MenuBar": QMenuBar,
    "RadioButton": QRadioButton,
    "DialogButtonBox": QDialogButtonBox,
    "GroupBox": QGroupBox,
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

WRAPPED_TYPES = {}

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

    def create_element(self, type_name: str) -> Any:
        """Create an element for the given type."""
        # Make sure that an app exists before any widgets
        # are created. Otherwise we might experience a
        # hard segfault.

        # TODO: create dynamic subclasses (meta) which implement
        # insert, set_attribute and remove
        # Make sure to 'cache' the generated types in a dict or something to
        # ensure equality
        QtCore.QCoreApplication.instance() or QtWidgets.QApplication()
        # TODO: how to do spacing / stretch?
        if type_name in ["Spacing", "Stretch"]:
            return QSpacerItem(0, 0)

        if type_name in WRAPPED_TYPES:
            return WRAPPED_TYPES[type_name]()

        original_type = name_to_type(type_name)
        wrapped_type = type(
            type_name,
            (original_type,),
            {
                "insert": INSERT_MAPPING.get(type_name, not_implemented),
                "remove": REMOVE_MAPPING.get(type_name, not_implemented),
                # Note: set_attribute defaults now to set_attr
                "set_attribute": SET_ATTR_MAPPING.get(type_name, set_attr),
            },
        )
        WRAPPED_TYPES[type_name] = wrapped_type
        return wrapped_type()

    def insert(self, el: Any, parent: Any, anchor: Any = None):
        """
        Add element `el` as a child to the element `parent`.
        If an anchor is specified, it inserts `el` before the `anchor`
        element.
        """
        if isinstance(el, QtWidgets.QMainWindow):
            # If the inserted element is a window, then there is
            # no real parent to add it to, so let's just show the
            # window element and be done with it.
            el.show()
            return

        parent.insert(el, anchor=anchor)

    def remove(self, el: Any, parent: Any):
        """Remove the element `el` from the children of the element `parent`."""
        parent.remove(el)

    def set_attribute(self, el: Any, attr: str, value: Any):
        """Set the attribute `attr` of the element `el` to the value `value`."""
        # Support a custom attribute 'layout_direction' so that we can
        # set the layout direction of the layout of the given element
        el.set_attribute(attr, value)

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
