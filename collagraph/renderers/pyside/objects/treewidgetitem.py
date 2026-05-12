from PySide6.QtWidgets import QTreeWidgetItem

from ... import PySideRenderer
from .qobject import set_attribute as qobject_set_attribute


def _snapshot_item_state(
    item: QTreeWidgetItem,
) -> list[tuple[QTreeWidgetItem, bool, bool]]:
    """Record ``(isExpanded, isSelected)`` for ``item`` and all descendants.

    Qt resets both bits across a ``removeChild``, so callers snapshot
    here before removing and restore after re-inserting (the path
    keyed-v-for reordering takes).
    """
    snapshot: list[tuple[QTreeWidgetItem, bool, bool]] = []

    def walk(it: QTreeWidgetItem) -> None:
        snapshot.append((it, it.isExpanded(), it.isSelected()))
        for i in range(it.childCount()):
            walk(it.child(i))

    walk(item)
    return snapshot


def _restore_item_state(
    snapshot: list[tuple[QTreeWidgetItem, bool, bool]],
) -> None:
    for it, expanded, selected in snapshot:
        it.setExpanded(expanded)
        it.setSelected(selected)


@PySideRenderer.register_insert(QTreeWidgetItem)
def insert(self, el: QTreeWidgetItem, anchor=None):
    if not isinstance(el, QTreeWidgetItem):
        raise NotImplementedError(f"No insert defined for: {type(el).__name__}")

    tree_widget = self.treeWidget()
    if tree_widget:
        tree_widget.blockSignals(True)

    try:
        if anchor is not None:
            index = self.indexOfChild(anchor)
            if self.treeWidget():
                # ``el`` may already be in the tree (legacy code paths
                # call insert without removing first); snapshot so we
                # can preserve its expansion/selection across removeChild.
                state = _snapshot_item_state(el)
                self.removeChild(el)
                self.insertChild(index, el)
                _restore_item_state(state)
            else:
                self.insertChild(index, el)
        else:
            self.addChild(el)

        # Restore state snapshotted at remove-time (keyed reorder via a
        # separate remove/insert pair, see remove() below).
        if hasattr(el, "_state_snapshot"):
            _restore_item_state(el._state_snapshot)
            del el._state_snapshot

        # After mounting, process some attributes that can only be
        # adjusted when the item is mounted in the tree structure.
        if hasattr(el, "_expanded"):
            el.setExpanded(el._expanded)
            delattr(el, "_expanded")

        if hasattr(el, "_selected"):
            el.setSelected(el._selected)
            delattr(el, "_selected")
    finally:
        if tree_widget:
            tree_widget.blockSignals(False)


@PySideRenderer.register_remove(QTreeWidgetItem)
def remove(self, el: QTreeWidgetItem):
    tree_widget = self.treeWidget()
    if tree_widget:
        tree_widget.blockSignals(True)

    try:
        # Stash UI state so a paired insert() (keyed reorder) can put
        # the subtree back the way it was. The stash is consumed by
        # the next insert of ``el``; if the item is being removed for
        # good the attribute is garbage-collected with it.
        el._state_snapshot = _snapshot_item_state(el)
        self.removeChild(el)
    finally:
        if tree_widget:
            tree_widget.blockSignals(False)


@PySideRenderer.register_set_attr(QTreeWidgetItem)
def set_attribute(self, attr, value):
    # Before setting any attribute, make sure to disable
    # all signals for the tree widget
    tree_widget = self.treeWidget()
    if tree_widget:
        tree_widget.blockSignals(True)

    try:
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
    finally:
        # And don't forget to enable signals when done
        if tree_widget:
            tree_widget.blockSignals(False)
