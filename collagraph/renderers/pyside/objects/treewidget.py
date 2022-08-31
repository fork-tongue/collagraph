from PySide6.QtWidgets import QTreeWidgetItem

from .treewidgetitem import insert as item_insert, remove as item_remove


def insert(self, el: QTreeWidgetItem, anchor=None):
    if not isinstance(el, QTreeWidgetItem):
        raise NotImplementedError(f"No insert defined for: {type(el).__name__}")

    root = self.invisibleRootItem()
    item_insert(root, el, anchor)


def remove(self, el: QTreeWidgetItem):
    root = self.invisibleRootItem()
    item_remove(root, el)
