from PySide6.QtWidgets import QWidget


def insert(self, el: QWidget, anchor=None):
    el.setParent(self)
    self.setWidget(el)


def remove(self, el: QWidget):
    self.setWidget(None)
    el.setParent(None)
