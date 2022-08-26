from PySide6.QtWidgets import QTreeWidgetItem

from .qobject import set_attribute as qobject_set_attribute
from .treewidgetitem import insert as item_insert, remove as item_remove


def insert(self, el: QTreeWidgetItem, anchor=None):
    if not isinstance(el, QTreeWidgetItem):
        raise NotImplementedError(f"No insert defined for: {type(el).__name__}")

    root = self.invisibleRootItem()
    item_insert(root, el, anchor)


def remove(self, el: QTreeWidgetItem):
    root = self.invisibleRootItem()
    item_remove(root, el)


def set_attribute(self, attr, value):
    qobject_set_attribute(self, attr, value)
