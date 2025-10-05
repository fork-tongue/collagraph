from PySide6.QtGui import QStandardItemModel

from ... import PySideRenderer


@PySideRenderer.register_insert(QStandardItemModel)
def insert(self, el, anchor=None):
    if isinstance(self, QStandardItemModel):
        if hasattr(el, "model_index"):
            row, column = getattr(el, "model_index")
            self.setItem(row, column, el)
            return

        if anchor is not None:
            index = self.indexFromItem(anchor)
            self.insertRow(index.row(), el)
        else:
            self.appendRow(el)
    else:
        raise NotImplementedError(type(self).__name__)


@PySideRenderer.register_remove(QStandardItemModel)
def remove(self, el):
    index = self.indexFromItem(el)
    self.takeRow(index.row())
