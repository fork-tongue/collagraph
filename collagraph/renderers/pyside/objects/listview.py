from PySide6.QtGui import QStandardItemModel


def insert(self, el: QStandardItemModel, anchor=None):
    el.setParent(self)
    self.setModel(el)


def remove(self, el):
    self.setModel(None)
