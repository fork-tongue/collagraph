from PySide6.QtWidgets import QMenu


def insert(self, el: QMenu, anchor: QMenu = None):
    # TODO: support separators
    if anchor:
        self.insertMenu(anchor, el)
    else:
        self.addMenu(el)
