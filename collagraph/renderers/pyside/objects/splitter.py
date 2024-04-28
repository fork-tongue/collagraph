from PySide6.QtWidgets import QSplitter, QWidget

from ... import PySideRenderer


@PySideRenderer.register_insert(QSplitter)
def insert(self, el: QWidget, anchor: QWidget = None):
    if anchor is not None:
        index = self.indexOf(anchor)
        self.insertWidget(index, el)
        el.setParent(self)
    else:
        self.addWidget(el)
        el.setParent(self)


@PySideRenderer.register_remove(QSplitter)
def remove(self, el: QWidget):
    el.setParent(None)
