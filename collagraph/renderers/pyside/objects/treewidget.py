from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from ... import PySideRenderer
from .treewidgetitem import insert as item_insert
from .treewidgetitem import remove as item_remove


@PySideRenderer.register_insert(QTreeWidget)
def insert(self, el: QTreeWidgetItem, anchor=None):
    if not isinstance(el, QTreeWidgetItem):
        raise NotImplementedError(f"No insert defined for: {type(el).__name__}")

    self.blockSignals(True)

    root = self.invisibleRootItem()
    item_insert(root, el, anchor)

    self.blockSignals(False)


@PySideRenderer.register_remove(QTreeWidget)
def remove(self, el: QTreeWidgetItem):
    self.blockSignals(True)

    root = self.invisibleRootItem()
    item_remove(root, el)

    self.blockSignals(False)
