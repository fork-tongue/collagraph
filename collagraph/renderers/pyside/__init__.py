from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenuBar,
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
