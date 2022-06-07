from PySide6.QtWidgets import QDockWidget, QMenuBar, QToolBar


def insert(self, el, anchor=None):
    # If the parent is a QMainWindow, then depending on the
    # type of child, we can add the element in special ways
    if isinstance(el, QDockWidget):
        # FIXME: how to specify area?
        # parent.addDockWidget(area, el)
        pass
    elif isinstance(el, QToolBar):
        # FIXME: how to specify area?
        # parent.addToolBar(area, el)
        self.addToolBar(el)
    elif isinstance(el, QMenuBar):
        self.setMenuBar(el)
        el.setParent(self)
    else:
        # Let's assume any other given widget is just the
        # central widget of the QMainWindow
        self.setCentralWidget(el)
        el.setParent(self)
