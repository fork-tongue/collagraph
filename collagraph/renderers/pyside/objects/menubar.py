from PySide6.QtWidgets import QMenu


def insert(self, el: QMenu, anchor: QMenu = None):
    if anchor is not None:
        action = self.insertMenu(anchor, el)
    else:
        action = self.addMenu(el)
    # Use the window property of the menubar to set
    # the parent of the action. Instead of keeping
    # a hierarchy of widgets, instead the hierarchy
    # is constructed with just the (menu)actions.
    # Using the widgets works fine on macOS, but causes
    # problems on Windows where menus would show on top
    # of each other.
    action.setParent(self.window())


def remove(self, el: QMenu):
    el.clear()
    menu_action = el.menuAction()
    self.removeAction(menu_action)
    menu_action.setParent(None)
