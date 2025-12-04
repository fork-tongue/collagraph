from PySide6.QtWidgets import QTreeWidgetItem

from ... import PySideRenderer
from .qobject import set_attribute as qobject_set_attribute


@PySideRenderer.register_insert(QTreeWidgetItem)
def insert(self, el: QTreeWidgetItem, anchor=None):
    if not isinstance(el, QTreeWidgetItem):
        raise NotImplementedError(f"No insert defined for: {type(el).__name__}")

    tree_widget = self.treeWidget()
    tree_widget and tree_widget.blockSignals(True)

    if anchor is not None:
        index = self.indexOfChild(anchor)
        if self.treeWidget():
            self.removeChild(el)
        self.insertChild(index, el)
    else:
        self.addChild(el)

    # After mounting, process some attributes that can only
    # be adjusted when the item is mounted in the tree structure
    if hasattr(el, "_expanded"):
        el.setExpanded(el._expanded)
        delattr(el, "_expanded")

    if hasattr(el, "_selected"):
        el.setSelected(el._selected)
        delattr(el, "_selected")

    tree_widget and tree_widget.blockSignals(False)


@PySideRenderer.register_remove(QTreeWidgetItem)
def remove(self, el: QTreeWidgetItem):
    tree_widget = self.treeWidget()
    tree_widget and tree_widget.blockSignals(True)

    self.removeChild(el)

    tree_widget and tree_widget.blockSignals(False)


@PySideRenderer.register_set_attr(QTreeWidgetItem)
def set_attribute(self, attr, value):
    # Before setting any attribute, make sure to disable
    # all signals for the tree widget
    tree_widget = self.treeWidget()
    tree_widget and tree_widget.blockSignals(True)

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
    tree_widget and tree_widget.blockSignals(False)
