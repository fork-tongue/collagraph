from functools import lru_cache

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QTextEdit,
    QTreeView,
    QWidget,
)


# Pre-populated cache for types
TYPE_MAPPING = {
    "button": QPushButton,
    "checkbox": QCheckBox,
    "combobox": QComboBox,
    "label": QLabel,
    "lineedit": QLineEdit,
    "menu": QMenu,
    "menubar": QMenuBar,
    "radiobutton": QRadioButton,
    "dialogbuttonbox": QDialogButtonBox,
    "groupbox": QGroupBox,
    "progessbar": QProgressBar,
    "slider": QSlider,
    "spinbox": QSpinBox,
    "statusbar": QStatusBar,
    "textedit": QTextEdit,
    "treeview": QTreeView,
    "widget": QWidget,
    "window": QMainWindow,
}

# Default arguments for types that need
# constructor arguments
DEFAULT_ARGS = {
    QtGui.QAction: (("",), {}),
}


@lru_cache(maxsize=None)
def name_to_type(name, modules=None, orig=None):
    """Lookup a class/type from PySide6 for the given name.

    See TYPE_MAPPING for some default names that you can use for
    DOM elements. It is also possible to use the complete PySide6
    class name instead, such as 'QWidget', 'QLine' or
    'QBoxLayout.Direction.TopToBottom'. As long as the name can
    be found in teh QtWidget, QtGui, QtCore or QtCore.Qt module.
    """
    if name.lower() in TYPE_MAPPING:
        return TYPE_MAPPING[name.lower()]
    if modules is None:
        modules = [QtWidgets, QtGui, QtCore, QtCore.Qt]
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


def camel_case(event, split):
    parts = event.split(split)
    return "".join([parts[0]] + [part.capitalize() for part in parts[1:]])


@lru_cache(maxsize=None)
def attr_name_to_method_name(name, setter=False):
    sep = "-"
    if "_" in name:
        sep = "_"

    prefix = f"set{sep}" if setter else ""
    return camel_case(f"{prefix}{name}", sep)


def call_method(method, args):
    """Method that allows for calling setters/methods with multiple arguments
    such as: `setColumnStretch` of `PySide6.QtWidgets.QGridLayout` which takes a
    column and stretch argument.
    """
    if isinstance(args, tuple):
        method(*args)
    else:
        method(args)
