from collections import defaultdict
import logging
from typing import Any, Callable

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QAction, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QBoxLayout,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QListView,
    QMainWindow,
    QMenu,
    QMenuBar,
    QSplitter,
    QTableView,
    QTabWidget,
    QTreeView,
    QWidget,
)

from . import Renderer
from .pyside.objects import (
    action,
    dialogbuttonbox,
    itemmodel,
    listview,
    menu,
    menubar,
    splitter,
    tab,
    widget,
    window,
)
from .pyside.utils import (
    camel_case,
    DEFAULT_ARGS,
    name_to_type,
    TYPE_MAPPING,
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
        QDialogButtonBox: dialogbuttonbox.insert,
        QTabWidget: tab.insert,
        QMenuBar: menubar.insert,
        QMenu: menu.insert,
        QListView: listview.insert,
        QTableView: listview.insert,
        QTreeView: listview.insert,
        QSplitter: splitter.insert,
        QStandardItemModel: itemmodel.insert,
    }
)
REMOVE_MAPPING = sorted_on_class_hierarchy(
    {
        QWidget: widget.remove,
        QTabWidget: tab.remove,
        QListView: listview.remove,
        QTableView: listview.remove,
        QTreeView: listview.remove,
        QMenuBar: menubar.remove,
        QMenu: menu.remove,
        QStandardItemModel: itemmodel.remove,
    }
)
SET_ATTR_MAPPING = sorted_on_class_hierarchy(
    {
        QWidget: widget.set_attribute,
        QAction: action.set_attribute,
        QStandardItem: widget.set_attribute,
        QStandardItemModel: widget.set_attribute,
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


class EventFilter(QtCore.QObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_handlers = defaultdict(set)

    def add_event_handler(self, event, handler):
        self.event_handlers[event].add(handler)

    def remove_event_handler(self, event, handler):
        self.event_handlers[event].remove(handler)

    def eventFilter(self, obj, event):  # noqa: N802
        event_name = event.type().name.decode()
        if handlers := self.event_handlers[event_name]:
            for handler in handlers.copy():
                handler(event)

        return super().eventFilter(obj, event)


def create_instance(pyside_type):
    """Creates an instance of the given type with the any default
    arguments (if any) passed into the constructor."""
    args, kwargs = DEFAULT_ARGS.get(pyside_type, ((), {}))
    return pyside_type(*args, **kwargs)


class PySideRenderer(Renderer):
    """PySide6 renderer."""

    def __init__(self, autoshow=True):
        super().__init__()
        self.autoshow = autoshow

    def register(self, type_name, custom_type):
        # Check that the custom type is a subclass of QWidget.
        # This ensures that the custom widget can be properly wrapped
        # and will get the `insert`, `remove` and `set_attribute`
        # methods.
        if QWidget not in custom_type.__mro__:
            raise TypeError(f"Specified type '{custom_type}' not a subclass of QWidget")
        TYPE_MAPPING[type_name.lower()] = custom_type

    def create_element(self, type_name: str) -> Any:
        """Create an element for the given type."""
        # Make sure that an app exists before any widgets
        # are created. Otherwise we might experience a
        # hard segfault.
        if not hasattr(self, "_app"):
            self._app = QtCore.QCoreApplication.instance() or QtWidgets.QApplication()

        # Create dynamic subclasses which implement `insert`, `set_attribute`
        # and `remove` methods.
        # The generated types are cached in WRAPPED_TYPES so they only have
        # to be generated once and can be used in equality comparisons
        if type_name in WRAPPED_TYPES:
            return create_instance(WRAPPED_TYPES[type_name])

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
        # Update the default arguments map with the new wrapped type
        DEFAULT_ARGS[wrapped_type] = DEFAULT_ARGS.get(original_type, ((), {}))

        return create_instance(WRAPPED_TYPES[type_name])

    def insert(self, el: Any, parent: Any, anchor: Any = None):
        """
        Add element `el` as a child to the element `parent`.
        If an anchor is specified, it inserts `el` before the `anchor`
        element.
        When the parent is a QApplication, then the element will be treated
        as a top-level widget with no parent and shown immediately.
        Use the `autoshow` attribute on the renderer to configure whether to
        show these wdigets automatically.
        """
        if isinstance(parent, QtWidgets.QApplication):
            # If the parent is a QApplication, then there is
            # no real parent to add it to, so let's just show the
            # widget (or window) element and be done with it.
            if self.autoshow:  # pragma: no cover
                el.show()
            return

        parent.insert(el, anchor=anchor)

    def remove(self, el: Any, parent: Any):
        """Remove the element `el` from the children of the element `parent`."""
        if isinstance(parent, QtWidgets.QApplication):
            el.close()
            return
        parent.remove(el)

    def set_attribute(self, el: Any, attr: str, value: Any):
        """Set the attribute `attr` of the element `el` to the value `value`."""
        # Support a custom attribute 'layout_direction' so that we can
        # set the layout direction of the layout of the given element
        el.set_attribute(attr, value)

    def remove_attribute(self, el: Any, attr: str, value: Any):
        """Remove the attribute `attr` from the element `el`."""
        raise NotImplementedError

    def add_event_listener(self, el: Any, event_type: str, value: Callable):
        """Add event listener for `event_type` to the element `el`."""
        signal_name = camel_case(event_type, "_")

        # Try and get the signal from the object
        signal = getattr(el, signal_name, None)
        if signal and hasattr(signal, "connect"):
            # Add a slots attribute to hold all the generated slots, keyed on event_type
            if not hasattr(el, "slots"):
                el.slots = defaultdict(set)

            # Create a slot with the given value
            # Note that the slot apparently does not need arguments to specify the type
            # or amount of arguments the enclosed callback needs. If the callback has
            # arguments, then those will be set to the parameter(s) of the signal when
            # it is emitted.
            try:
                # Creating a slot of a bound method on an instance (that is not
                # a QObject?) results in a SystemError. Lambdas though _can_ function
                # as a slot, so when creating a slot of the value fails, retry with
                # a simple lambda.
                slot = QtCore.Slot()(value)
            except SystemError:
                # TODO: with some inspection we might be able to figure out the
                # signature of the 'value' function and adjust the lambda accordingly
                slot = QtCore.Slot()(lambda *args: value(*args))
            el.slots[event_type].add(slot)

            signal.connect(slot)
        else:
            if not hasattr(el, "_event_filter"):
                el._event_filter = EventFilter()
                el.installEventFilter(el._event_filter)
            event_name = camel_case(event_type, "_", upper=True)
            el._event_filter.add_event_handler(event_name, value)

    def remove_event_listener(self, el: Any, event_type: str, value: Callable):
        """Remove event listener for `event_type` to the element `el`."""
        signal_name = camel_case(event_type, "_")

        signal = getattr(el, signal_name, None)
        if not signal or not hasattr(signal, "connect"):
            event_name = camel_case(event_type, "_", upper=True)
            el._event_filter.remove_event_handler(event_name, value)
            return

        for slot in el.slots[event_type]:
            # Slot can be compared to its value
            if slot == value:
                signal.disconnect(slot)
                el.slots[event_type].remove(slot)
                break
