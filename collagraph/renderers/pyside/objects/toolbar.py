from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget


def insert(self, el, anchor=None):
    if isinstance(el, QWidget):
        if anchor is not None:
            action = self.insertWidget(anchor, el)
        else:
            action = self.addWidget(el)
        action.setParent(self)
    elif isinstance(el, QAction):
        if anchor is not None:
            self.insertAction(anchor, el)
        else:
            self.addAction(el)
        el.setParent(self.window())


def remove(self, el):
    if isinstance(el, QAction):
        self.removeAction(el)
        el.setParent(None)
    elif isinstance(el, QWidget):
        el.setParent(None)
