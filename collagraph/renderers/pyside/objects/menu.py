from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu


def insert(self, el, anchor=None):
    if isinstance(el, QMenu):
        if anchor:
            action = self.insertMenu(anchor, el)
        else:
            action = self.addMenu(el)
        action.setParent(self.menuAction())
    elif isinstance(el, QAction):
        if anchor:
            self.insertAction(anchor, el)
        else:
            self.addAction(el)
        el.setParent(self.menuAction())


def remove(self, el):
    if isinstance(el, QAction):
        self.removeAction(el)
        el.setParent(None)
    elif isinstance(el, QMenu):
        el.clear()
        menu_action = el.menuAction()
        self.removeAction(menu_action)
        menu_action.setParent(None)
