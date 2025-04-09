from typing import Union

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QListView, QTableView, QTreeView

from ... import PySideRenderer


@PySideRenderer.register_insert(QListView, QTableView, QTreeView)
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


@PySideRenderer.register_remove(QListView, QTableView, QTreeView)
def remove(self, el: Union[QStandardItemModel, QItemSelectionModel]):
    if isinstance(el, QStandardItemModel):
        self.setModel(None)
    elif isinstance(el, QItemSelectionModel):
        # Note: setting the selection model to None results
        # in a segmentation fault, hard crash...
        # Setting the selection model to a new instance will instead
        # print a warning:
        # > QAbstractItemView::setSelectionModel() failed: Trying to set a selection
        # > model, which works on a different model than the view.
        # Maybe just not removing is sufficient
        # self.setSelectionModel(QItemSelectionModel())
        # self.setSelectionModel(QItemSelectionModel(self.model()))
        pass
    else:
        raise NotImplementedError(type(el).__name__)

    el.setParent(None)
