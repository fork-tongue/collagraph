from collections import defaultdict
import logging
from typing import Any, Callable

from PySide6 import QtCore, QtWidgets

from . import Renderer


logger = logging.getLogger(__name__)


def name_to_type(name, modules=None):
    # IDEA: use a dict as cache (or lru_cache). Might speed things up a bit?
    # Using a dict might be handy, because we can specify certain types in advance?
    if modules is None:
        modules = [QtWidgets, QtCore, QtCore.Qt]
    parts = name.split(".")
    for module in modules:
        if element_class := getattr(module, parts[0], None):
            if len(parts) > 1:
                return name_to_type(".".join(parts[1:]), modules=[element_class])
            return element_class

    raise TypeError(f"Couldn't find type for name: '{name}'")


def attr_name_to_method_name(name, setter=False):
    parts = name.split("-")
    prefix = parts[0].lower() if not setter else f"set{parts[0].capitalize()}"
    rest = "".join([p.capitalize() for p in parts[1:]])
    return f"{prefix}{rest}"


class PySideRenderer(Renderer):
    """PySide6 renderer."""

    def create_element(self, type: str) -> Any:
        """Create an element for the given type."""
        # Make sure that an app exists before any widgets
        # are created. Otherwise we might experience a
        # hard segfault.
        QtCore.QCoreApplication.instance() or QtWidgets.QApplication()
        return name_to_type(type)()

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

        # Adding a widget to a widget involves getting the layout of the parent
        # and then inserting the widget into the layout. The layout might not
        # exist yet, so let's create a default QBoxLayout.
        # TODO: add support for other layouts? Maybe through special/custom attributes?
        layout = parent.layout()
        if not layout:
            layout = QtWidgets.QBoxLayout(
                QtWidgets.QBoxLayout.Direction.LeftToRight, parent
            )

        index = -1
        if anchor:
            index = layout.indexOf(anchor)

        if hasattr(layout, "insertWidget"):
            # QBoxLayout and QStackedLayout support `insertWidget(index, widget)`
            layout.insertWidget(index, el)
        else:
            # Try and support other layouts (all QLayout subclasses should
            # support `addWidget` and `takeAt`). This is a really dump and
            # inefficient way of updating the layout, but it might work?
            if index == -1:
                layout.addWidget(el)
            else:
                # Pop items until we can add, then re-add
                # all the popped items.
                popped_items = []
                count = layout.count()
                disparity = count - index
                for i in range(count, disparity, -1):
                    # takeAt returns layout items, not widgets
                    item = layout.takeAt(i)
                    popped_items.append(item)

                layout.addWidget(el)
                for item in popped_items:
                    layout.addItem(item)

    def remove(self, el: Any, parent: Any):
        """Remove the element `el` from the children of the element `parent`."""
        layout = parent.layout()
        layout.removeWidget(el)

    def set_attribute(self, el: Any, attr: str, value: Any):
        """Set the attribute `attr` of the element `el` to the value `value`."""
        # Support a custom attribute 'layout_direction' so that we can
        # set the layout direction of the layout of the given element
        if attr == "layout_direction":
            direction = name_to_type(value)
            if layout := el.layout():
                layout.setDirection(direction)
            else:
                el.setLayout(QtWidgets.QBoxLayout(direction))
            return

        method_name = attr_name_to_method_name(attr, setter=True)
        method = getattr(el, method_name, None)
        if not method:
            return

        if isinstance(value, str):
            try:
                value = name_to_type(value)
            except TypeError:
                pass
            method(value)
        else:
            try:
                method(value)
            except TypeError:
                # TODO: Maybe also call name_to_type on all values?
                method(*value)

    def remove_attribute(self, el: Any, attr: str, value: Any):
        """Remove the attribute `attr` from the element `el`."""
        # TODO: what does it mean to remove an attribute? How to define default values?
        pass

    def add_event_listener(self, el: Any, event_type: str, value: Callable):
        """Add event listener for `event_type` to the element `el`."""
        if not value:
            return

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
