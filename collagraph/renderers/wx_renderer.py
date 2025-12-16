import logging
from collections import defaultdict
from functools import lru_cache, partial
from typing import Any, Callable
from warnings import warn

import wx

from collagraph.constants import EventLoopType

from . import Renderer
from .wx import attr_name_to_method_name, call_method, camel_case

logger = logging.getLogger(__name__)

# Pre-populated cache for types, mapping from string to type
TYPE_MAPPING = {
    "button": wx.Button,
    "checkbox": wx.CheckBox,
    "combobox": wx.ComboBox,
    "frame": wx.Frame,
    "label": wx.StaticText,
    "lineedit": wx.TextCtrl,
    "menu": wx.Menu,
    "menubar": wx.MenuBar,
    "radiobutton": wx.RadioButton,
    "progessbar": wx.Gauge,
    "slider": wx.Slider,
    "statusbar": wx.StatusBar,
    "textedit": wx.TextCtrl,
    "toolbar": wx.ToolBar,
    "widget": wx.Frame,
    "window": wx.Window,
}

# Mapping from type to func (list of tuples actually instead of dict)
INSERT_MAPPING = []
REMOVE_MAPPING = []
SET_ATTR_MAPPING = []
LAYOUT_MAPPING = {}


# Default arguments for types that need
# constructor arguments
# Note: For most widgets, we'll need to provide a parent
# during creation. We use a placeholder that will be replaced
# in create_instance
DEFAULT_ARGS = {}

# Cache for wrapped types
WRAPPED_TYPES = {}

# Default values for attributes. Used when an attribute
# is 'removed', then the default value (if one exists)
# is restored.
DEFAULT_VALUES = {}

# Custom methods that are registered for specific attribute names
CUSTOM_ATTRIBUTES = {}


class WxRenderer(Renderer):
    """wxPython renderer."""

    def __init__(self, autoshow=True):
        super().__init__()
        self.autoshow = autoshow

    def preferred_event_loop_type(self):
        return EventLoopType.DEFAULT

    def register_asyncio(self):
        # TODO: Implement asyncio integration for wxPython
        # wxPython doesn't have built-in asyncio support like PySide6
        # Consider using libraries like wxasync if async support is needed
        pass

    @classmethod
    def register_element(cls, type_name, typ=None):
        """Register a typ that can be created as an element"""
        if typ is None:

            def wrapper(typ):
                cls.register_element(type_name, typ=typ)
                return typ

            return wrapper

        type_name = normalize_name(type_name)
        if type_name in TYPE_MAPPING:
            warn(f"{type_name} element already registered")
        # Check that the custom type is a subclass of wx.Window.
        # This ensures that the custom widget can be properly wrapped
        # and will get the `insert`, `remove` and `set_attribute`
        # methods.
        if wx.Window not in typ.__mro__:
            raise TypeError(f"Specified type '{typ}' not a subclass of wx.Window")

        TYPE_MAPPING[type_name] = typ

    @classmethod
    def register_layout(cls, layout_name, typ=None):
        """Register a typ that can be used as a layout type"""
        if typ is None:

            def wrapper(typ):
                cls.register_layout(layout_name, typ=typ)
                return typ

            return wrapper

        layout_name = normalize_name(layout_name)
        if layout_name in LAYOUT_MAPPING:
            warn(f"{layout_name} layout already registered")
        # Check that the custom type is a subclass of wx.Sizer.
        # This ensures that the custom sizer can be properly wrapped
        # and will get the `insert`, `remove` and `set_attribute`
        # methods.
        if wx.Sizer not in typ.__mro__:
            raise TypeError(f"Specified type '{typ}' not a subclass of wx.Sizer")

        LAYOUT_MAPPING[layout_name] = typ

    @classmethod
    def register_custom_attribute(cls, *names, func=None):
        """Register a custom method to run for the given attribute names"""
        if len(names) >= 1 and func is None:

            def wrapper(func):
                cls.register_custom_attribute(*names, func=func)
                return func

            return wrapper

        if func is None:
            *names, func = names

        for name in names:
            CUSTOM_ATTRIBUTES[name] = func

    @classmethod
    def register_insert(cls, *types, func=None):
        """Register a function for given types for inserting an item
        into the hierarchy"""
        if len(types) >= 1 and func is None:

            def wrapper(func):
                cls.register_insert(*types, func=func)
                return func

            return wrapper

        if func is None:
            *types, func = types

        for t in types:
            for index, mapping in enumerate(INSERT_MAPPING):
                if mapping[0] == t:
                    warn(f"{t} already registered for 'insert'")
                    break

            INSERT_MAPPING.append((t, func))
            INSERT_MAPPING.sort(key=class_hierarchy)

    @classmethod
    def register_remove(cls, *types, func=None):
        """Register a function for the given types for removing an
        item from the hierarchy"""
        if len(types) >= 1 and func is None:

            def wrapper(func):
                cls.register_remove(*types, func=func)
                return func

            return wrapper

        if func is None:
            *types, func = types

        for t in types:
            for index, mapping in enumerate(REMOVE_MAPPING):
                if mapping[0] == t:
                    warn(f"{t} already registered for 'remove'")
                    break

            REMOVE_MAPPING.append((t, func))
            REMOVE_MAPPING.sort(key=class_hierarchy)

    @classmethod
    def register_set_attr(cls, *typ, func=None):
        """Register a function for the given types for setting
        an attribute"""
        if len(typ) >= 1 and func is None:

            def wrapper(func):
                cls.register_set_attr(*typ, func=func)
                return func

            return wrapper

        if func is None:
            *typ, func = typ

        for t in typ:
            for index, mapping in enumerate(SET_ATTR_MAPPING):
                if mapping[0] == t:
                    warn(f"{t} already registered for 'set_attribute'")
                    break

            SET_ATTR_MAPPING.append((t, func))
            SET_ATTR_MAPPING.sort(key=class_hierarchy)

    def create_element(self, type_name: str) -> Any:
        """Create an element for the given type."""
        # Make sure that an app exists before any widgets
        # are created. Otherwise we might experience a
        # hard segfault.
        # if not hasattr(self, "_app"):
        #     self._app = wx.App()

        return self.create_object(type_name)

    @classmethod
    def create_object(cls, type_name: str) -> Any:
        """Create an element for the given type."""
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
        for key, mapping in maps.items():
            for cls, method in mapping:
                if issubclass(original_type, cls):
                    attrs[key] = method
                    break
            else:
                bloeb = partial(not_implemented, context=key)
                attrs[key] = bloeb

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
        if isinstance(parent, wx.App):
            # If the parent is a QApplication, then there is
            # no real parent to add it to, so let's just show the
            # widget (or window) element and be done with it.
            if self.autoshow:  # pragma: no cover
                el.Show()
            return

        if isinstance(el, wx.Dialog):
            el.setParent(parent, el.windowFlags())
            el.Show()
            return

        parent.insert(el, anchor=anchor)

    def remove(self, el: Any, parent: Any):
        """Remove the element `el` from the children of the element `parent`."""
        if isinstance(parent, wx.App):
            el.close()
            return

        if isinstance(el, wx.Dialog):
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

        # Check for registered methods for custom attributes
        if set_attr := CUSTOM_ATTRIBUTES.get(attr):
            set_attr(el, attr, value)
            return

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

        # Add a handlers attribute to track event handlers
        if not hasattr(el, "_event_handlers"):
            el._event_handlers = defaultdict(list)

        # Store the handler
        el._event_handlers[event_type].append(value)

        # Map common event types to wx event types
        # Some events need to pass the event object to the handler
        event_map = {
            "clicked": (wx.EVT_BUTTON, False),
            "checked": (wx.EVT_CHECKBOX, False),
            "toggled": (wx.EVT_CHECKBOX, False),
            "text_changed": (wx.EVT_TEXT, True),
            "text": (wx.EVT_TEXT, True),
            "scroll": (wx.EVT_SCROLL, True),
            "scroll_changed": (wx.EVT_SCROLL_CHANGED, True),
            "selected": (wx.EVT_COMBOBOX, True),
            "choice": (wx.EVT_CHOICE, True),
            "radiobutton": (wx.EVT_RADIOBUTTON, False),
            # Add more mappings as needed
        }

        event_info = event_map.get(event_type)
        if event_info:
            wx_event, pass_event = event_info
            if pass_event:
                el.Bind(wx_event, lambda event: value(event))
            else:
                el.Bind(wx_event, lambda event: value())
        else:
            logger.warning(f"Unknown event type: {event_type}")

    def remove_event_listener(self, el: Any, event_type: str, value: Callable):
        """Remove event listener for `event_type` to the element `el`."""
        event_type = event_type.replace("-", "_")

        if hasattr(el, "_event_handlers") and event_type in el._event_handlers:
            try:
                el._event_handlers[event_type].remove(value)
            except ValueError:
                logger.warning(f"Handler not found for event type: {event_type}")

        # TODO: Implement proper unbinding in wxPython
        # wxPython's Unbind is more complex than PySide's disconnect
        logger.debug(f"Event listener removal for {event_type} needs proper implementation")


def not_implemented(self, context, *args, **kwargs):
    """Default 'not implemented' error for wrapped types"""
    raise NotImplementedError(
        f"{type(self).__name__}.{context}", f"ARGS: {args}, KWARGS: {kwargs}"
    )


_temp_parent = None


def get_temp_parent():
    """Get or create a temporary hidden parent for widgets that need one during creation."""
    global _temp_parent
    if _temp_parent is None:
        _temp_parent = wx.Frame(None, title="Temp")
        _temp_parent.Hide()
    return _temp_parent


def create_instance(wx_type: Callable):
    """Creates an instance of the given type with the any default
    arguments (if any) passed into the constructor."""
    args, kwargs = DEFAULT_ARGS.get(wx_type, ((), {}))

    # For top-level windows (Frame, Dialog), use None as parent
    # For other widgets, use a temporary parent that will be replaced during insert
    parent = None
    if wx_type not in (wx.Frame, wx.Dialog):
        parent = get_temp_parent()

    return wx_type(parent, *args, **kwargs)


def normalize_name(name):
    """Transforms given name to lower case and removes underscores and dashes"""
    return name.lower().replace("_", "").replace("-", "")


def class_hierarchy(value):
    """Returns the (negated) count of all the classes that a class inherits."""
    # __mro__ is a tuple of all the classes that a class inherits. The longer the
    # __mro__, the 'deeper' the subclass is, so we can use that to sort the classes
    # to make the deepest class come first.
    return -len(value[0].__mro__)


@lru_cache(maxsize=None)
def name_to_type(name, modules=None, orig=None):
    """Lookup a class/type from PySide6 for the given name.

    See TYPE_MAPPING for some default names that you can use for
    DOM elements. It is also possible to use the complete PySide6
    class name instead, such as 'QWidget', 'QLine' or
    'QBoxLayout.Direction.TopToBottom'. As long as the name can
    be found in the QtWidget, QtGui, QtCore or QtCore.Qt module.
    """
    normalized_name = normalize_name(name)
    if normalized_name in TYPE_MAPPING:
        return TYPE_MAPPING[normalized_name]
    if normalized_name in LAYOUT_MAPPING:
        return LAYOUT_MAPPING[normalized_name]
    if modules is None:
        modules = [wx]
    parts = name.split(".")
    for module in modules:
        # Try the get the attribute as-is from the module
        element_class = getattr(module, parts[0], None)
        if element_class is None:
            # If that fails, try to do a case insensitive search
            # through the `dir` of the module
            part = parts[0].lower()
            for attribute in dir(module):
                if part == attribute.lower():
                    element_class = getattr(module, attribute)
                    break

        if element_class is not None:
            if len(parts) > 1:
                return name_to_type(
                    ".".join(parts[1:]), modules=[element_class], orig=name
                )
            return element_class

    raise TypeError(f"Couldn't find type for name: '{name}' ({orig})")


@WxRenderer.register_insert(wx.Window)
def insert(self, el, anchor=None):
    el.Reparent(self)

    # Adding a widget (el) to a widget (self) involves getting the sizer
    # of the parent (self) and then inserting the widget into the sizer.
    # The sizer might not exist yet, so let's create a default Box.
    sizer = self.GetSizer()
    if not sizer:
        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer)

    # TODO: anchor
    # sizer.Add(el, anchor=anchor)
    el.Show()

    # Add with default spacing: 5px border on all sides, expand horizontally
    sizer.Add(el, proportion=0, flag=wx.ALL | wx.EXPAND, border=5)

    # Trigger layout update so widgets are positioned correctly
    sizer.Layout()
    self.Layout()


@WxRenderer.register_set_attr(wx.Object)
def basic_set_attribute(self, attr, value):
    method_name = attr_name_to_method_name(attr, setter=True)
    method = getattr(self, method_name, None)
    if not method:
        logger.debug(f"Setting custom attr: {attr}, {method_name}")
        setattr(self, attr, value)
        return

    call_method(method, value)


@WxRenderer.register_set_attr(wx.TextEntry)
def text_entry_set_attribute(self, attr, value):
    if attr in ("text", "value"):
        self.SetValue(value)
        return

    basic_set_attribute(self, attr, value)


@WxRenderer.register_set_attr(wx.ComboBox)
def combobox_set_attribute(self, attr, value):
    if attr == "choices":
        # Clear existing items and add new ones
        self.Clear()
        if value:
            self.AppendItems(value)
        return
    elif attr == "value":
        # Set the current selection by string value
        self.SetValue(value)
        return

    basic_set_attribute(self, attr, value)
