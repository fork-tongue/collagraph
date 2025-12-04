from PySide6.QtWidgets import QTreeWidgetItem

from ... import PySideRenderer
from .qobject import set_attribute as qobject_set_attribute


@PySideRenderer.register_insert(QTreeWidgetItem)
def insert(self, el: QTreeWidgetItem, anchor=None):
    if not isinstance(el, QTreeWidgetItem):
        raise NotImplementedError(f"No insert defined for: {type(el).__name__}")

    if anchor is not None:
        index = self.indexOfChild(anchor)
        # Only remove if el is actually a child (not already removed)
        if self.indexOfChild(el) >= 0:
            self.removeChild(el)
        self.insertChild(index, el)
    else:
        self.addChild(el)

    # After insertion, restore state that was saved during removal (for moves/reorders)
    if hasattr(el, "_saved_selected") or hasattr(el, "_saved_expanded"):
        if hasattr(el, "_saved_selected"):
            el.setSelected(el._saved_selected)
            delattr(el, "_saved_selected")
        if hasattr(el, "_saved_expanded"):
            el.setExpanded(el._saved_expanded)
            delattr(el, "_saved_expanded")
    else:
        # Initial mounting - use temp attributes set before mounting
        if hasattr(el, "_expanded"):
            el.setExpanded(el._expanded)
            delattr(el, "_expanded")
        if hasattr(el, "_selected"):
            el.setSelected(el._selected)
            delattr(el, "_selected")


@PySideRenderer.register_remove(QTreeWidgetItem)
def remove(self, el: QTreeWidgetItem):
    # Save selection/expanded state before removing
    # because Qt clears these when the item is detached
    # These will be restored when the item is re-inserted (for moves/reorders)
    if el.treeWidget() is not None:
        el._saved_selected = el.isSelected()
        el._saved_expanded = el.isExpanded()
    self.removeChild(el)


@PySideRenderer.register_set_attr(QTreeWidgetItem)
def set_attribute(self, attr, value):
    # Before setting any attribute, make sure to disable
    # all signals for the tree widget
    tree_widget = self.treeWidget()
    if tree_widget:
        tree_widget.blockSignals(True)

    match attr:
        case "content":
            for col, data in value.items():
                self.setText(col, data)
        case "expanded":
            if not tree_widget:
                self._expanded = value
            else:
                self.setExpanded(value)
        case "selected":
            if not tree_widget:
                self._selected = value
            else:
                self.setSelected(value)
        case _:
            qobject_set_attribute(self, attr, value)

    # And don't forget to enable signals when done
    if tree_widget:
        tree_widget.blockSignals(False)
