from PySide6.QtWidgets import QScrollArea, QWidget

from ... import PySideRenderer


@PySideRenderer.register_insert(QScrollArea)
def insert(self, el: QWidget, anchor=None):
    el.setParent(self)
    self.setWidget(el)


@PySideRenderer.register_remove(QScrollArea)
def remove(self, el: QWidget):
    self.setWidget(None)
    el.setParent(None)
