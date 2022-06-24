from PySide6.QtWidgets import QDockWidget, QMenuBar, QStatusBar, QToolBar


def insert(self, el, anchor=None):
    # If the parent is a QMainWindow, then depending on the
    # type of child, we can add the element in special ways
    if isinstance(el, QDockWidget):
        if area := getattr(el, "area", None):
            self.addDockWidget(area, el)
        else:
            raise NotImplementedError("Dock widgets need 'area' attribute")
        el.setParent(self)
    elif isinstance(el, QToolBar):
        if area := getattr(el, "area", None):
            self.addToolBar(el, area)
        else:
            self.addToolBar(el)
        el.setParent(self)
    elif isinstance(el, QMenuBar):
        self.setMenuBar(el)
        el.setParent(self)
    elif isinstance(el, QStatusBar):
        self.setStatusBar(el)
        el.setParent(self)
    else:
        # Let's assume any other given widget is just the
        # central widget of the QMainWindow
        self.setCentralWidget(el)
        el.setParent(self)
