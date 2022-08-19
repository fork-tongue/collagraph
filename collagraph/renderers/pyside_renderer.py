from collections import defaultdict
import logging
from typing import Any, Callable

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QBoxLayout, QFormLayout, QGridLayout, QWidget

from collagraph.types import EventLoopType
from . import Renderer
from .pyside.objects import (
    combobox,
    dialogbuttonbox,
    dockwidget,
    itemmodel,
    listview,
    menu,
    menubar,
    qobject,
    splitter,
    standarditem,
    statusbar,
    tab,
    toolbar,
    widget,
    window,
)
from .pyside.utils import (
    attr_name_to_method_name,
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
        QtWidgets.QWidget: widget.insert,
        QtWidgets.QMainWindow: window.insert,
        QtWidgets.QDialogButtonBox: dialogbuttonbox.insert,
        QtWidgets.QTabWidget: tab.insert,
        QtWidgets.QMenuBar: menubar.insert,
        QtWidgets.QMenu: menu.insert,
        QtWidgets.QListView: listview.insert,
        QtWidgets.QTableView: listview.insert,
        QtWidgets.QTreeView: listview.insert,
        QtWidgets.QSplitter: splitter.insert,
        QtGui.QStandardItemModel: itemmodel.insert,
        QtGui.QStandardItem: standarditem.insert,
        QtWidgets.QStatusBar: statusbar.insert,
        QtWidgets.QToolBar: toolbar.insert,
        QtWidgets.QDockWidget: dockwidget.insert,
    }
)
REMOVE_MAPPING = sorted_on_class_hierarchy(
    {
        QtWidgets.QWidget: widget.remove,
        QtWidgets.QTabWidget: tab.remove,
        QtWidgets.QListView: listview.remove,
        QtWidgets.QTableView: listview.remove,
        QtWidgets.QTreeView: listview.remove,
        QtWidgets.QMenuBar: menubar.remove,
        QtWidgets.QMenu: menu.remove,
        QtGui.QStandardItemModel: itemmodel.remove,
        QtGui.QStandardItem: standarditem.remove,
        QtWidgets.QStatusBar: statusbar.remove,
        QtWidgets.QToolBar: toolbar.remove,
        QtWidgets.QDockWidget: dockwidget.remove,
    }
)
SET_ATTR_MAPPING = sorted_on_class_hierarchy(
    {
        QtWidgets.QWidget: widget.set_attribute,
        QtGui.QAction: qobject.set_attribute,
        QtGui.QStandardItem: standarditem.set_attribute,
        QtGui.QStandardItemModel: qobject.set_attribute,
        QtCore.QItemSelectionModel: qobject.set_attribute,
        QtWidgets.QDialogButtonBox: dialogbuttonbox.set_attribute,
        QtWidgets.QComboBox: combobox.set_attribute,
        QtWidgets.QStatusBar: statusbar.set_attribute,
    }
)

# Cache for wrapped types
WRAPPED_TYPES = {}

DEFAULT_VALUES = {}

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

    def preferred_event_loop_type(self):
        return EventLoopType.QT

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

    def create_text_element(self):
        raise NotImplementedError

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

        if isinstance(el, QtWidgets.QDialog):
            el.setParent(parent, el.windowFlags())
            el.show()
            return

        parent.insert(el, anchor=anchor)

    def remove(self, el: Any, parent: Any):
        """Remove the element `el` from the children of the element `parent`."""
        if isinstance(parent, QtWidgets.QApplication):
            el.close()
            return

        if isinstance(el, QtWidgets.QDialog):
            # Hide the dialog to make sure it's not visible anymore
            el.hide()
            # Then mark the element for deletion, so that it won't trigger
            # any of 'finished', 'done', 'rejected', 'accepted' signals.
            el.deleteLater()
            return

        parent.remove(el)

    def set_element_text(self, el: Any, value: str):
        raise NotImplementedError

    def set_attribute(self, el: Any, attr: str, value: Any):
        """Set the attribute `attr` of the element `el` to the value `value`."""

        key = f"{type(el).__name__}.{attr}"
        if key not in DEFAULT_VALUES:
            if not hasattr(el, "metaObject"):
                logger.debug(f"{el} does not have metaObject")
            else:
                method_name = attr_name_to_method_name(attr, setter=False)

                meta_object = el.metaObject()
                property_idx = meta_object.indexOfProperty(method_name)
                if property_idx >= 0:
                    meta_property = meta_object.property(property_idx)
                    result = meta_property.read(el)
                    DEFAULT_VALUES[key] = (meta_property, result)
                else:
                    logger.debug(f"'{attr}' is not a Qt property on {type(el)}")

        # Support a custom attribute 'layout_direction' so that we can
        # set the layout direction of the layout of the given element
        el.set_attribute(attr, value)

    def remove_attribute(self, el: Any, attr: str, value: Any):
        """Remove the attribute `attr` from the element `el`."""
        # Make it possible to delete custom attributes
        if hasattr(el, attr):
            if getattr(el, attr) == value:
                delattr(el, attr)
                return

        key = f"{type(el).__name__}.{attr}"
        if key in DEFAULT_VALUES:
            meta_property, default_value = DEFAULT_VALUES[key]
            meta_property.write(el, default_value)
            return

        raise NotImplementedError(f"Can't remove {attr}: {value}")

    def add_event_listener(self, el: Any, event_type: str, value: Callable):
        """Add event listener for `event_type` to the element `el`."""
        event_type = event_type.replace("-", "_")
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
        event_type = event_type.replace("-", "_")
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
