from PySide6.QtGui import QStandardItemModel

from ... import PySideRenderer


def _get_view_from_model(model: QStandardItemModel):
    """Get the view associated with this model."""
    from PySide6.QtWidgets import QListView, QTableView, QTreeView

    # The model's parent should be the view
    parent = model.parent()
    if isinstance(parent, (QTreeView, QListView, QTableView)):
        return parent

    return None


def _restore_all_selections(model: QStandardItemModel):
    """Restore selections for all items in the model that have _saved_selected=True."""
    view = _get_view_from_model(model)
    if not view:
        return

    from PySide6.QtCore import QItemSelectionModel

    selection_model = view.selectionModel()

    # Clear all selections first
    selection_model.clear()

    # Find all items that should be selected and select them
    for row in range(model.rowCount()):
        item = model.item(row)
        if item and hasattr(item, "_saved_selected") and item._saved_selected:
            index = model.indexFromItem(item)
            selection_model.select(
                index,
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
            delattr(item, "_saved_selected")


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

        # Defer selection restoration until after ALL items are inserted
        # because inserting items shifts row indices around
        if hasattr(el, "_saved_selected"):
            if el._saved_selected:
                # Keep the attribute for later restoration

                # Check if this is the last item with saved selection state
                # Only check after inserting an item that WAS selected
                has_pending = False
                for row in range(self.rowCount()):
                    item = self.item(row)
                    if item and item != el and hasattr(item, "_saved_selected"):
                        has_pending = True
                        break

                if not has_pending:
                    # This is the last item with saved selection
                    # - restore all selections now
                    _restore_all_selections(self)
            else:
                delattr(el, "_saved_selected")

        # Expanded state can be restored immediately since it doesn't interfere
        if hasattr(el, "_saved_expanded"):
            view = _get_view_from_model(self)
            if view:
                from PySide6.QtWidgets import QTreeView

                if isinstance(view, QTreeView):
                    index = self.indexFromItem(el)
                    view.setExpanded(index, el._saved_expanded)
            delattr(el, "_saved_expanded")
        else:
            # Initial mounting - use temp attributes set before mounting
            if hasattr(el, "_expanded"):
                view = _get_view_from_model(self)
                if view:
                    from PySide6.QtWidgets import QTreeView

                    if isinstance(view, QTreeView):
                        index = self.indexFromItem(el)
                        view.setExpanded(index, el._expanded)
                delattr(el, "_expanded")

            if hasattr(el, "_selected"):
                view = _get_view_from_model(self)
                if view:
                    from PySide6.QtCore import QItemSelectionModel

                    index = self.indexFromItem(el)
                    selection_model = view.selectionModel()
                    if el._selected:
                        selection_model.select(
                            index,
                            QItemSelectionModel.SelectionFlag.Select
                            | QItemSelectionModel.SelectionFlag.Rows,
                        )
                delattr(el, "_selected")
    else:
        raise NotImplementedError(type(self).__name__)


@PySideRenderer.register_remove(QStandardItemModel)
def remove(self, el):
    # Save selection/expanded state before removing
    # because Qt clears these when the item is detached from the model
    # These will be restored when the item is re-inserted (for moves/reorders)
    view = _get_view_from_model(self)
    if view:
        from PySide6.QtWidgets import QTreeView

        index = self.indexFromItem(el)

        selection_model = view.selectionModel()
        el._saved_selected = selection_model.isSelected(index)

        if isinstance(view, QTreeView):
            el._saved_expanded = view.isExpanded(index)

    index = self.indexFromItem(el)
    self.takeRow(index.row())
