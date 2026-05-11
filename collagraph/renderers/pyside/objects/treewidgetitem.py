from PySide6.QtWidgets import QTreeWidgetItem

from ... import PySideRenderer
from .qobject import set_attribute as qobject_set_attribute


def _snapshot_expansion(item: QTreeWidgetItem) -> list[tuple[QTreeWidgetItem, bool]]:
    """Record ``isExpanded`` for ``item`` and all its descendants.

    Qt collapses an entire subtree when ``removeChild`` is called on its
    root, so callers snapshot the state here before removing and restore
    it after re-inserting (keyed v-for reordering).
    """
    snapshot: list[tuple[QTreeWidgetItem, bool]] = []

    def walk(it: QTreeWidgetItem) -> None:
        snapshot.append((it, it.isExpanded()))
        for i in range(it.childCount()):
            walk(it.child(i))

    walk(item)
    return snapshot


def _restore_expansion(snapshot: list[tuple[QTreeWidgetItem, bool]]) -> None:
    for it, expanded in snapshot:
        it.setExpanded(expanded)


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
                # can preserve its expansion across removeChild.
                expansion = _snapshot_expansion(el)
                self.removeChild(el)
                self.insertChild(index, el)
                _restore_expansion(expansion)
            else:
                self.insertChild(index, el)
        else:
            self.addChild(el)

        # Restore expansion that was snapshotted at remove-time (keyed
        # reorder via a separate remove/insert pair, see remove() below).
        if hasattr(el, "_expansion_snapshot"):
            _restore_expansion(el._expansion_snapshot)
            del el._expansion_snapshot

        # After mounting, process some attributes that can only
        # be adjusted when the item is mounted in the tree structure
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
        # Stash expansion so a paired insert() (keyed reorder) can put
        # the subtree back the way it was. The stash is consumed by the
        # next insert of ``el``; if the item is being removed for good
        # the attribute is simply garbage-collected with it.
        el._expansion_snapshot = _snapshot_expansion(el)
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
