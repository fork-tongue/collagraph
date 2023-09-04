from PySide6 import QtWidgets

from . import widget
from ... import PySideRenderer


@PySideRenderer.register_set_attr(QtWidgets.QComboBox)
def set_attribute(self, attr, value):
    if attr == "items":
        self.addItems(value)
    else:
        widget.set_attribute(self, attr, value)
