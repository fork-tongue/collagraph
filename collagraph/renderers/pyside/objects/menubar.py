from PySide6.QtWidgets import QMenu


def insert(self, el: QMenu, anchor: QMenu = None):
    if anchor:
        self.insertMenu(anchor, el)
    else:
        self.addMenu(el)
    el.setParent(self)


def remove(self, el: QMenu):
    el.clear()
    menu_action = el.menuAction()
    self.removeAction(menu_action)
    el.setParent(None)
