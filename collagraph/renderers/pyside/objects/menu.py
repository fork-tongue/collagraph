from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu


def insert(self, el, anchor=None):
    if isinstance(el, QMenu):
        if anchor:
            self.insertMenu(anchor, el)
        else:
            self.addMenu(el)
    elif isinstance(el, QAction):
        if anchor:
            self.insertAction(anchor, el)
        else:
            self.addAction(el)
    el.setParent(self)


def remove(self, el):
    if isinstance(el, QAction):
        self.removeAction(el)
    elif isinstance(el, QMenu):
        el.clear()
        menu_action = el.menuAction()
        self.removeAction(menu_action)
    el.setParent(None)
