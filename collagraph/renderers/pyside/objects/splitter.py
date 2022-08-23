from PySide6.QtWidgets import QWidget


def insert(self, el: QWidget, anchor: QWidget = None):
    if anchor is not None:
        index = self.indexOf(anchor)
        self.insertWidget(index, el)
        el.setParent(self)
    else:
        self.addWidget(el)
        el.setParent(self)


def remove(self, el: QWidget):
    el.setParent(None)
