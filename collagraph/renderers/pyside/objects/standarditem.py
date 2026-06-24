from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QStandardItem
from PySide6.QtWidgets import QListView, QTableView, QTreeView

from ... import PySideRenderer
from .qobject import set_attribute as qobject_set_attribute


def _get_view_from_item(item: QStandardItem):
    model = item.model()
    if not model:
        return None

    parent = model.parent()
    if isinstance(parent, (QTreeView, QListView, QTableView)):
        return parent
    return None


def _snapshot_item_state(item: QStandardItem):
    model = item.model()
    view = _get_view_from_item(item)
    if not (model and view):
        return None

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


def _apply_item_selection(item: QStandardItem, selected: bool) -> None:
    model = item.model()
    view = _get_view_from_item(item)
    if not (model and view):
        item._selected = selected
        return

    selection_model = view.selectionModel()
    index = model.indexFromItem(item)
    flags = QItemSelectionModel.SelectionFlag.Rows
    if selected:
        flags |= QItemSelectionModel.SelectionFlag.Select
    else:
        flags |= QItemSelectionModel.SelectionFlag.Deselect
    selection_model.select(index, flags)


def _apply_item_expanded(item: QStandardItem, expanded: bool) -> None:
    model = item.model()
    view = _get_view_from_item(item)
    if not (model and isinstance(view, QTreeView)):
        item._expanded = expanded
        return

    index = model.indexFromItem(item)
    view.setExpanded(index, expanded)


def _restore_item_state(item: QStandardItem) -> None:
    if not hasattr(item, "_state_snapshot"):
        return

    model = item.model()
    view = _get_view_from_item(item)
    if not (model and view):
        return

    snapshot = item._state_snapshot
    for it, expanded, _selected in snapshot:
        if isinstance(view, QTreeView):
            index = model.indexFromItem(it)
            view.setExpanded(index, expanded)
    for it, _expanded, selected in snapshot:
        index = model.indexFromItem(it)
        flags = QItemSelectionModel.SelectionFlag.Rows
        if selected:
            flags |= QItemSelectionModel.SelectionFlag.Select
        else:
            flags |= QItemSelectionModel.SelectionFlag.Deselect
        view.selectionModel().select(index, flags)

    del item._state_snapshot


@PySideRenderer.register_insert(QStandardItem)
def insert(self, el, anchor=None):
    if hasattr(el, "model_index"):
        row, column = getattr(el, "model_index")
        self.setChild(row, column, el)
        return

    if anchor is not None:
        index = None
        for row in range(self.rowCount()):
            if anchor is self.child(row):
                index = row
                break
        if index is None:
            return
        if el.row() >= 0 and el.parent() == self:
            self.takeRow(el.row())
        self.insertRow(index, el)
    else:
        self.appendRow(el)

    _restore_item_state(el)

    if hasattr(el, "_expanded"):
        _apply_item_expanded(el, el._expanded)
        delattr(el, "_expanded")

    if hasattr(el, "_selected"):
        _apply_item_selection(el, el._selected)
        delattr(el, "_selected")


@PySideRenderer.register_remove(QStandardItem)
def remove(self, el):
    snapshot = _snapshot_item_state(el)
    if snapshot is not None:
        el._state_snapshot = snapshot

    if hasattr(el, "model_index"):
        # Only support removal of rows for now
        row, _column = getattr(el, "model_index")
        if model := el.model():
            index = model.indexFromItem(el)
            row = index.row()

        self.takeRow(row)
        return

    self.takeRow(el.row())


@PySideRenderer.register_set_attr(QStandardItem)
def set_attribute(self, attr, value):
    # Before setting any attribute, make sure to disable
    # all signals for the associated model
    model = self.model()
    if model:
        model.blockSignals(True)

    try:
        match attr:
            case "selected":
                _apply_item_selection(self, value)
                return
            case "expanded":
                _apply_item_expanded(self, value)
                return

        if attr == "model_index" and model:
            index = model.indexFromItem(self)
            row, column = value
            if index.row() != row or index.column() != column:
                if parent := self.parent():
                    # `it` is `self`
                    it = parent.takeChild(index.row(), index.column())
                    parent.setChild(row, column, self)
                else:
                    # `it` is `self`
                    it = model.takeItem(index.row(), index.column())
                    model.setItem(row, column, it)

        qobject_set_attribute(self, attr, value)
    finally:
        # And don't forget to enable signals when done
        if model:
            model.blockSignals(False)
