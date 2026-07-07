"""Custom QTreeWidget subclass used by the drag-and-drop example.

Qt's built-in ``InternalMove`` drop behaviour would mutate the
``QTreeWidget`` directly, side-stepping our reactive state. Instead we
intercept ``dropEvent``, compute the source/target paths in tree-index
space and emit a ``itemDropped`` signal so the component can mutate the
state itself; the renderer then rebuilds the tree from state.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

import collagraph as cg


def _path_for_item(tree_widget: QtWidgets.QTreeWidget, item) -> list[int]:
    """Compute the integer path of a tree item (e.g. ``[1, 0, 2]``)."""
    if item is None:
        return []
    path: list[int] = []
    current = item
    while current is not None:
        parent = current.parent()
        if parent is None:
            path.append(tree_widget.indexOfTopLevelItem(current))
            break
        path.append(parent.indexOfChild(current))
        current = parent
    path.reverse()
    return path


_POSITION_MAP = {
    QtWidgets.QAbstractItemView.AboveItem: "above",
    QtWidgets.QAbstractItemView.BelowItem: "below",
    QtWidgets.QAbstractItemView.OnItem: "on",
    QtWidgets.QAbstractItemView.OnViewport: "viewport",
}


class DragDropTreeWidget(QtWidgets.QTreeWidget):
    """A QTreeWidget that turns drops into a state-mutation signal.

    The signal payload is ``(source_paths, target_path, position)``:
    * ``source_paths`` — paths of the items that were dragged
    * ``target_path`` — path of the item the drop is anchored to
      (empty list when dropping onto the viewport)
    * ``position`` — ``"above"``, ``"below"``, ``"on"`` or ``"viewport"``
    """

    # Qt signal naming style is mixedCase; tell pep8-naming to leave it alone.
    itemDropped = QtCore.Signal(list, list, str)  # noqa: N815

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def dropEvent(self, event):
        target_item = self.itemAt(event.position().toPoint())
        target_path = _path_for_item(self, target_item)
        position = _POSITION_MAP.get(self.dropIndicatorPosition(), "viewport")

        source_paths = [_path_for_item(self, item) for item in self.selectedItems()]

        # Suppress Qt's own move; the state mutation will rebuild the tree.
        event.ignore()
        self.itemDropped.emit(source_paths, target_path, position)


# Register the custom widget so it's usable as ``<dnd-treewidget>`` in
# templates. Registering on import keeps the example self-contained.
cg.PySideRenderer.register_element("dnd-treewidget", DragDropTreeWidget)
