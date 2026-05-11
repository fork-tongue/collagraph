"""Tree-model logic for the drag-and-drop tree-widget example.

The whole tree is stored as plain ``TreeNode`` instances whose ``children``
attribute is an ``observ`` reactive list. The functions below operate on
that structure and produce mutations that the renderer can pick up.

Keeping these operations in a pure-Python module (no Qt, no collagraph)
makes them easy to TDD — see ``tests/test_tree_dnd_model.py``.
"""

from __future__ import annotations

from itertools import count

from observ import reactive

# Module-level id generator so newly added nodes get stable :key values for
# the v-for keyed reconciliation in the .cgx template.
_id_counter = count(1)


def _next_id() -> int:
    return next(_id_counter)


class TreeNode:
    """A single node in the tree.

    ``children`` is a reactive list, so the framework can observe
    mutations (append / insert / pop) and rebuild the affected
    sub-tree without us having to touch the QTreeWidget directly.
    """

    __slots__ = ("children", "id", "label")

    def __init__(self, label: str, children: list["TreeNode"] | None = None):
        self.id = _next_id()
        self.label = label
        self.children = reactive(list(children) if children else [])

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"TreeNode({self.label!r}, id={self.id})"


# --------------------------------------------------------------------------- #
# path helpers
# --------------------------------------------------------------------------- #


def get_node(tree, path):
    """Return the node at ``path`` within ``tree``.

    ``path`` is a list of indices: ``[2, 0]`` means
    ``tree[2].children[0]``.
    """
    node = tree[path[0]]
    for idx in path[1:]:
        node = node.children[idx]
    return node


def _parent_list_and_index(tree, path):
    """Return the reactive list that contains ``path`` and the final index."""
    items = tree
    for idx in path[:-1]:
        items = items[idx].children
    return items, path[-1]


def find_path(tree, target):
    """Depth-first search for ``target``; return its path or ``None``."""

    def walk(items, prefix):
        for idx, node in enumerate(items):
            if node is target:
                return [*prefix, idx]
            found = walk(node.children, [*prefix, idx])
            if found is not None:
                return found
        return None

    return walk(tree, [])


# --------------------------------------------------------------------------- #
# selection / path-set utilities
# --------------------------------------------------------------------------- #


def prune_descendants(paths):
    """Remove paths whose ancestor is also in the set.

    Returns a list of unique paths (as lists). Order is not specified
    — callers that care should sort the result.
    """
    unique = {tuple(p) for p in paths}
    pruned = []
    for p in unique:
        if any(p[:i] in unique for i in range(1, len(p))):
            continue
        pruned.append(list(p))
    return pruned


# --------------------------------------------------------------------------- #
# mutations
# --------------------------------------------------------------------------- #


def add_item(tree, parent_path, label):
    """Append a new ``TreeNode(label)`` under ``parent_path``.

    ``parent_path`` of ``[]`` adds the item at the root level.
    """
    new_node = TreeNode(label)
    if not parent_path:
        tree.append(new_node)
    else:
        get_node(tree, parent_path).children.append(new_node)
    return new_node


def remove_items(tree, paths):
    """Remove every node referenced by ``paths``.

    Overlapping paths (a parent and a descendant both selected) are
    collapsed first so we only remove each subtree once.
    """
    pruned = prune_descendants(paths)
    # Sort descending so earlier removals don't invalidate later indices
    # within the same parent.
    for path in sorted(pruned, reverse=True):
        parent_list, idx = _parent_list_and_index(tree, path)
        parent_list.pop(idx)


def regroup_selection(tree, paths, label="Group"):
    """Wrap the roots of ``paths`` in a new group at the first root's spot.

    The returned node is the freshly created group (or ``None`` when
    the selection is empty).
    """
    roots = sorted(prune_descendants(paths))
    if not roots:
        return None

    # Grab references before mutating; paths become stale otherwise.
    nodes = [get_node(tree, p) for p in roots]
    anchor_path = roots[0]
    anchor_parent_list, anchor_idx = _parent_list_and_index(tree, anchor_path)

    # Remove originals deepest/last-first so indices stay valid.
    for path in sorted(roots, reverse=True):
        parent_list, idx = _parent_list_and_index(tree, path)
        parent_list.pop(idx)

    new_group = TreeNode(label, children=nodes)
    # The anchor parent list shrank by however many siblings of the
    # anchor (including itself) we removed; recompute the insertion
    # index by clamping into the (now-shorter) list.
    insert_idx = min(anchor_idx, len(anchor_parent_list))
    anchor_parent_list.insert(insert_idx, new_group)
    return new_group


def move_items(tree, source_paths, target_path, position):
    """Drag-and-drop move.

    ``position`` is one of ``"above"``, ``"below"``, ``"on"`` or
    ``"viewport"`` — mirroring ``QAbstractItemView.DropIndicatorPosition``.
    A drop on the viewport appends to the root list.

    Moves that would create a cycle (dropping a node into one of its
    own descendants) are silently dropped.
    """
    sources = sorted(prune_descendants(source_paths))
    if not sources:
        return

    # Filter out cycles: target must not be inside any source subtree.
    if target_path is not None:
        target_tuple = tuple(target_path)
        sources = [
            s
            for s in sources
            if target_tuple[: len(s)] != tuple(s)
        ]
        if not sources:
            return

    # Capture references before mutating.
    source_nodes = [get_node(tree, p) for p in sources]
    target_node = (
        get_node(tree, target_path)
        if target_path is not None and position != "viewport"
        else None
    )

    # Remove sources, deepest/last first.
    for path in sorted(sources, reverse=True):
        parent_list, idx = _parent_list_and_index(tree, path)
        parent_list.pop(idx)

    # Resolve the destination *after* the removal so indices reflect
    # reality.
    if position == "viewport" or target_node is None:
        dest_parent, dest_idx = tree, len(tree)
    elif position == "on":
        dest_parent = target_node.children
        dest_idx = len(target_node.children)
    else:
        new_target_path = find_path(tree, target_node)
        dest_parent, t_idx = _parent_list_and_index(tree, new_target_path)
        dest_idx = t_idx + (1 if position == "below" else 0)

    for offset, node in enumerate(source_nodes):
        dest_parent.insert(dest_idx + offset, node)
