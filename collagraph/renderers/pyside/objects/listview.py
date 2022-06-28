from typing import Union

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QStandardItemModel


def insert(self, el: Union[QStandardItemModel, QItemSelectionModel], anchor=None):
    if isinstance(el, QStandardItemModel):
        self.setModel(el)
    elif isinstance(el, QItemSelectionModel):
        if model := self.model():
            el.setModel(model)
            self.setSelectionModel(el)
        else:
            raise RuntimeError(
                "Can't set a selection model because no item model was set (yet). "
            )
    else:
        raise NotImplementedError(type(el).__name__)

    el.setParent(self)


def remove(self, el: Union[QStandardItemModel, QItemSelectionModel]):
    if isinstance(el, QStandardItemModel):
        self.setModel(None)
    elif isinstance(el, QItemSelectionModel):
        self.setSelectionModel(None)
    else:
        raise NotImplementedError(type(el).__name__)

    el.setParent(None)
