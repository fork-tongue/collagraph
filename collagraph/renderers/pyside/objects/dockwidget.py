from PySide6 import QtWidgets

from ... import PySideRenderer


@PySideRenderer.register_insert(QtWidgets.QDockWidget)
def insert(self, el, anchor=None):
    if getattr(el, "title", False):
        self.setTitleBarWidget(el)
    else:
        self.setWidget(el)
    el.setParent(self)


@PySideRenderer.register_remove(QtWidgets.QDockWidget)
def remove(self, el):
    el.setParent(None)
