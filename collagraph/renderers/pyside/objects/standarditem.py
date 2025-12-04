from PySide6.QtGui import QStandardItem

from ... import PySideRenderer
from .qobject import set_attribute as qobject_set_attribute


def _check_and_restore_selections(item):
    """Check if this is the last item with saved selection, and restore all if so."""
    model = item.model()
    if not model:
        return

    # Recursively check if any items still have pending _saved_selected attributes
    def has_pending_selections(check_item):
        if check_item and check_item != item and hasattr(check_item, "_saved_selected"):
            return True
        if check_item:
            for row in range(check_item.rowCount()):
                child = check_item.child(row)
                if has_pending_selections(child):
                    return True
        return False

    # Check all top-level items in the model
    has_pending = False
    for row in range(model.rowCount()):
        top_item = model.item(row)
        if has_pending_selections(top_item):
            has_pending = True
            break

    if not has_pending:
        # This is the last item - restore all selections now
        from .itemmodel import _restore_all_selections

        _restore_all_selections(model)


@PySideRenderer.register_insert(QStandardItem)
def insert(self, el, anchor=None):
    if hasattr(el, "model_index"):
        row, column = getattr(el, "model_index")
        self.setChild(row, column, el)
    elif anchor is not None:
        index = None
        for row in range(self.rowCount()):
            if anchor is self.child(row):
                index = row
                break
        if index is None:
            return
        # Only remove if el is actually a child (not already removed)
        if el.row() >= 0 and el.parent() == self:
            self.takeRow(el.row())
        self.insertRow(index, el)
    else:
        self.appendRow(el)

    # Defer selection restoration until after ALL items are inserted
    # (same approach as itemmodel.py)
    if hasattr(el, "_saved_selected"):
        if el._saved_selected:
            # Keep the attribute for later restoration
            # Check if this is the last item with saved selection
            _check_and_restore_selections(el)
        else:
            delattr(el, "_saved_selected")

    # Expanded state can be restored immediately since it doesn't interfere
    if hasattr(el, "_saved_expanded"):
        view = _get_view_from_item(el)
        if view:
            from PySide6.QtWidgets import QTreeView

            if isinstance(view, QTreeView):
                model = el.model()
                index = model.indexFromItem(el)
                view.setExpanded(index, el._saved_expanded)
        delattr(el, "_saved_expanded")
    else:
        # Initial mounting - use temp attributes set before mounting
        if hasattr(el, "_expanded"):
            view = _get_view_from_item(el)
            if view:
                from PySide6.QtWidgets import QTreeView

                if isinstance(view, QTreeView):
                    model = el.model()
                    index = model.indexFromItem(el)
                    view.setExpanded(index, el._expanded)
            delattr(el, "_expanded")

        if hasattr(el, "_selected"):
            view = _get_view_from_item(el)
            if view:
                from PySide6.QtCore import QItemSelectionModel

                model = el.model()
                index = model.indexFromItem(el)
                selection_model = view.selectionModel()
                if el._selected:
                    selection_model.select(
                        index,
                        QItemSelectionModel.SelectionFlag.Select
                        | QItemSelectionModel.SelectionFlag.Rows,
                    )
            delattr(el, "_selected")


@PySideRenderer.register_remove(QStandardItem)
def remove(self, el):
    # Save selection/expanded state before removing
    # because Qt clears these when the item is detached from the model
    # These will be restored when the item is re-inserted (for moves/reorders)
    view = _get_view_from_item(el)
    if view:
        from PySide6.QtWidgets import QTreeView

        model = el.model()
        index = model.indexFromItem(el)

        selection_model = view.selectionModel()
        el._saved_selected = selection_model.isSelected(index)

        if isinstance(view, QTreeView):
            el._saved_expanded = view.isExpanded(index)

    if hasattr(el, "model_index"):
        # Only support removal of rows for now
        row, _column = getattr(el, "model_index")
        if model := el.model():
            index = model.indexFromItem(el)
            row = index.row()

        self.takeRow(row)
        return

    self.takeRow(el.row())


def _get_view_from_item(item: QStandardItem):
    """Get the view associated with this item's model."""
    from PySide6.QtWidgets import QListView, QTableView, QTreeView

    model = item.model()
    if not model:
        return None

    # Search for a view that uses this model
    # The model's parent should be the view
    parent = model.parent()
    if isinstance(parent, (QTreeView, QListView, QTableView)):
        return parent

    return None


@PySideRenderer.register_set_attr(QStandardItem)
def set_attribute(self, attr, value):
    # Before setting any attribute, make sure to disable
    # all signals for the associated model
    model = self.model()
    if model:
        model.blockSignals(True)

    match attr:
        case "model_index":
            if model:
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
            else:
                # Store as attribute for later use during insert
                qobject_set_attribute(self, attr, value)
        case "selected":
            view = _get_view_from_item(self)
            if not view:
                # Item not in model yet, save for later
                self._selected = value
            else:
                from PySide6.QtCore import QItemSelectionModel

                selection_model = view.selectionModel()
                index = model.indexFromItem(self)

                if value:
                    selection_model.select(
                        index,
                        QItemSelectionModel.SelectionFlag.Select
                        | QItemSelectionModel.SelectionFlag.Rows,
                    )
                else:
                    selection_model.select(
                        index,
                        QItemSelectionModel.SelectionFlag.Deselect
                        | QItemSelectionModel.SelectionFlag.Rows,
                    )
        case "expanded":
            view = _get_view_from_item(self)
            if not view:
                # Item not in model yet, save for later
                self._expanded = value
            else:
                from PySide6.QtWidgets import QTreeView

                if isinstance(view, QTreeView):
                    index = model.indexFromItem(self)
                    view.setExpanded(index, value)
        case _:
            qobject_set_attribute(self, attr, value)

    # And don't forget to enable signals when done
    if model:
        model.blockSignals(False)
