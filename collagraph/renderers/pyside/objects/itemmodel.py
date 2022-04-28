from PySide6.QtGui import QStandardItemModel


def insert(self, el, anchor=None):
    if isinstance(self, QStandardItemModel):
        if index := getattr(el, "model_index", None):
            self.setItem(*index, el)
            return

        if anchor:
            index = self.indexFromItem(anchor)
            self.insertRow(index.row(), el)
        else:
            self.appendRow(el)
    else:
        raise NotImplementedError(type(self).__name__)


def remove(self, el):
    index = self.indexFromItem(el)
    self.takeRow(index.row())
