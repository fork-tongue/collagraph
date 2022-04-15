from collections import defaultdict
import logging
from typing import Any, Callable

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QBoxLayout,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QMainWindow,
    QMenu,
    QMenuBar,
    QSpacerItem,
    QTabWidget,
    QWidget,
)

from . import Renderer
from .pyside import (
    action,
    camel_case,
    dialog,
    menu,
    menubar,
    name_to_type,
    tab,
    widget,
    window,
)


logger = logging.getLogger(__name__)


def sorted_on_class_hierarchy(value):
    # __mro__ is a tuple of all the classes that an class inherits. The longer the
    # __mro__, the 'deeper' the subclass is, so we can use that to sort the classes
    # to make the deepest class come first.
    return dict(sorted(value.items(), key=lambda x: -len(x[0].__mro__)))


INSERT_MAPPING = sorted_on_class_hierarchy(
    {
        QWidget: widget.insert,
        QMainWindow: window.insert,
        QDialogButtonBox: dialog.insert,
        QTabWidget: tab.insert,
        QMenuBar: menubar.insert,
        QMenu: menu.insert,
    }
)
REMOVE_MAPPING = sorted_on_class_hierarchy(
    {
        QWidget: widget.remove,
        QTabWidget: tab.remove,
    }
)
SET_ATTR_MAPPING = sorted_on_class_hierarchy(
    {
        QWidget: widget.set_attribute,
        QAction: action.set_attribute,
    }
)

# Cache for wrapped types
WRAPPED_TYPES = {}

LAYOUT = {
    "Box": QBoxLayout,
    "Grid": QGridLayout,
    "Form": QFormLayout,
}


def not_implemented(self, *args, **kwargs):
    raise NotImplementedError(type(self).__name__)


class PySideRenderer(Renderer):
    """PySide6 renderer."""

    def create_element(self, type_name: str) -> Any:
        """Create an element for the given type."""
        # Make sure that an app exists before any widgets
        # are created. Otherwise we might experience a
        # hard segfault.
        QtCore.QCoreApplication.instance() or QtWidgets.QApplication()

        # TODO: how to do spacing / stretch?
        if type_name in ["Spacing", "Stretch"]:
            return QSpacerItem(0, 0)

        # if type_name in ["QAction", "Action"]:
        #     return QAction("")

        # Create dynamic subclasses which implement `insert`, `set_attribute`
        # and `remove` methods.
        # The generated types are cached in WRAPPED_TYPES so they only have
        # to be generated once and can be used in equality comparisons
        if type_name in WRAPPED_TYPES:
            return WRAPPED_TYPES[type_name]()

        original_type = name_to_type(type_name)

        attrs = {}
        maps = {
            "insert": INSERT_MAPPING,
            "remove": REMOVE_MAPPING,
            "set_attribute": SET_ATTR_MAPPING,
        }
        for key, map in maps.items():
            for cls, method in map.items():
                if issubclass(original_type, cls):
                    attrs[key] = method
                    break
            else:
                attrs[key] = not_implemented

        # Create the new type with the new methods
        wrapped_type = type(type_name, (original_type,), attrs)
        WRAPPED_TYPES[type_name] = wrapped_type
        if original_type == QAction:
            return wrapped_type("")
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
            setattr(el, "slots", defaultdict(set))

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
