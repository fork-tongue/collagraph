from PySide6.QtWidgets import QWidget


def insert(self, el: QWidget, anchor: QWidget = None):
    index = getattr(el, "tab_index", -1)
    label = getattr(el, "tab_label", "")

    if index >= 0:
        self.insertTab(index, el, label)
    else:
        self.addTab(el, label)


def remove(self, el: QWidget):
    index = self.indexOf(el)
    if index >= 0:
        self.removeTab(index)
