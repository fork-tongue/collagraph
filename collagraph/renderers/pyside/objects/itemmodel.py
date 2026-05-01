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

    # Recursively find all items that should be selected and select them
    def restore_item_selection(item):
        if item and hasattr(item, "_saved_selected") and item._saved_selected:
            index = model.indexFromItem(item)
            selection_model.select(
                index,
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
            delattr(item, "_saved_selected")

        # Recursively check children
        if item:
            for row in range(item.rowCount()):
                child = item.child(row)
                restore_item_selection(child)

    # Check all top-level items
    for row in range(model.rowCount()):
        item = model.item(row)
        restore_item_selection(item)


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

        # Check if this item or any of its children have saved selection state
        def has_saved_selection_recursive(item):
            if hasattr(item, "_saved_selected") and item._saved_selected:
                return True
            for row in range(item.rowCount()):
                child = item.child(row)
                if child and has_saved_selection_recursive(child):
                    return True
            return False

        # Check if the inserted item has any saved selections (including children)
        item_has_saved_selections = has_saved_selection_recursive(el)

        # Defer selection restoration until after ALL items are inserted
        # because inserting items shifts row indices around
        if item_has_saved_selections:
            # Keep the attributes for later restoration

            # Check if this is the last item with saved selection state
            # Only check after inserting an item that WAS selected
            # (or has selected children)
            def has_pending_selections_in_item(item, skip_item):
                """
                Recursively check if item or its children have pending _saved_selected.
                """
                if item and item != skip_item:
                    if hasattr(item, "_saved_selected") and item._saved_selected:
                        return True
                    for row in range(item.rowCount()):
                        child = item.child(row)
                        if has_pending_selections_in_item(child, skip_item):
                            return True
                return False

            has_pending = False
            for row in range(self.rowCount()):
                item = self.item(row)
                if has_pending_selections_in_item(item, el):
                    has_pending = True
                    break

            if not has_pending:
                # This is the last item with saved selection
                # - restore all selections now
                _restore_all_selections(self)
        elif hasattr(el, "_saved_selected"):
            # Item had _saved_selected but it was False - clean it up
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


def _save_item_state_recursively(item, view, model):
    """Recursively save selection/expanded state for an item and all its children."""
    from PySide6.QtWidgets import QTreeView

    index = model.indexFromItem(item)
    selection_model = view.selectionModel()

    # Save this item's state
    item._saved_selected = selection_model.isSelected(index)

    if isinstance(view, QTreeView):
        item._saved_expanded = view.isExpanded(index)

    # Recursively save children's state
    for row in range(item.rowCount()):
        child = item.child(row)
        if child:
            _save_item_state_recursively(child, view, model)


@PySideRenderer.register_remove(QStandardItemModel)
def remove(self, el):
    # Save selection/expanded state before removing
    # because Qt clears these when the item is detached from the model
    # These will be restored when the item is re-inserted (for moves/reorders)
    view = _get_view_from_model(self)
    if view:
        # Recursively save state for this item and all its children
        _save_item_state_recursively(el, view, self)

    index = self.indexFromItem(el)
    self.takeRow(index.row())
