from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QListView, QTableView, QTreeView

from ... import PySideRenderer


def _get_view_from_model(model: QStandardItemModel):
    parent = model.parent()
    if isinstance(parent, (QTreeView, QListView, QTableView)):
        return parent
    return None


def _snapshot_item_state(
    item: QStandardItem,
    model: QStandardItemModel,
    view,
) -> list[tuple[QStandardItem, bool, bool]]:
    snapshot: list[tuple[QStandardItem, bool, bool]] = []

    def walk(it: QStandardItem) -> None:
        index = model.indexFromItem(it)
        selected = view.selectionModel().isSelected(index)
        expanded = isinstance(view, QTreeView) and view.isExpanded(index)
        snapshot.append((it, expanded, selected))
        for row in range(it.rowCount()):
            child = it.child(row)
            if child:
                walk(child)

    walk(item)
    return snapshot


def _apply_item_selection(
    model: QStandardItemModel,
    view,
    item: QStandardItem,
    selected: bool,
) -> None:
    selection_model = view.selectionModel()
    index = model.indexFromItem(item)
    flags = QItemSelectionModel.SelectionFlag.Rows
    if selected:
        flags |= QItemSelectionModel.SelectionFlag.Select
    else:
        flags |= QItemSelectionModel.SelectionFlag.Deselect
    selection_model.select(index, flags)


def _apply_item_expanded(
    model: QStandardItemModel,
    view,
    item: QStandardItem,
    expanded: bool,
) -> None:
    if isinstance(view, QTreeView):
        index = model.indexFromItem(item)
        view.setExpanded(index, expanded)


def _restore_item_state(
    snapshot: list[tuple[QStandardItem, bool, bool]],
    model: QStandardItemModel,
    view,
) -> None:
    for item, expanded, _selected in snapshot:
        _apply_item_expanded(model, view, item, expanded)
    for item, _expanded, selected in snapshot:
        _apply_item_selection(model, view, item, selected)


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

        view = _get_view_from_model(self)
        if view:
            if hasattr(el, "_state_snapshot"):
                _restore_item_state(el._state_snapshot, self, view)
                del el._state_snapshot

            if hasattr(el, "_expanded"):
                _apply_item_expanded(self, view, el, el._expanded)
                delattr(el, "_expanded")

            if hasattr(el, "_selected"):
                _apply_item_selection(self, view, el, el._selected)
                delattr(el, "_selected")
    else:
        raise NotImplementedError(type(self).__name__)


@PySideRenderer.register_remove(QStandardItemModel)
def remove(self, el):
    view = _get_view_from_model(self)
    if view:
        el._state_snapshot = _snapshot_item_state(el, self, view)

    index = self.indexFromItem(el)
    self.takeRow(index.row())
