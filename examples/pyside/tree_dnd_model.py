"""Tree-model logic for the drag-and-drop tree-widget example.

Nodes are stored as plain Python dicts so the entire tree lives inside
one big reactive structure (the component's ``state``). Each node has
the keys ``id``, ``label`` and ``children`` (a list of child node
dicts). Per-node UI state like selection and expansion is intentionally
kept outside the node — the component tracks those separately as lists
of ids.

Keeping the operations in this module — no Qt, no collagraph — lets
them be exhaustively tested via ``tests/test_tree_dnd_model.py``.
"""

from __future__ import annotations

from itertools import count
from typing import Any

# Module-level id generator so each node has a stable :key value for
# the v-for keyed reconciliation in the .cgx template.
_id_counter = count(1)


def _next_id() -> int:
    return next(_id_counter)


Node = dict[str, Any]


def make_node(label: str, children: list[Node] | None = None) -> Node:
    """Create a fresh tree node as a plain dict."""
    return {
        "id": _next_id(),
        "label": label,
        "children": list(children) if children else [],
    }


# --------------------------------------------------------------------------- #
# path helpers
# --------------------------------------------------------------------------- #


def get_node(tree, path):
    """Return the node at ``path`` within ``tree``.

    ``path`` is a list of indices: ``[2, 0]`` means
    ``tree[2]["children"][0]``.
    """
    node = tree[path[0]]
    for idx in path[1:]:
        node = node["children"][idx]
    return node


def _parent_list_and_index(tree, path):
    """Return the children-list that contains ``path`` and the final index."""
    items = tree
    for idx in path[:-1]:
        items = items[idx]["children"]
    return items, path[-1]


def find_path(tree, target):
    """Depth-first search for ``target`` by identity. Returns ``None`` if absent."""

    def walk(items, prefix):
        for idx, node in enumerate(items):
            if node is target:
                return [*prefix, idx]
            found = walk(node["children"], [*prefix, idx])
            if found is not None:
                return found
        return None

    return walk(tree, [])


def find_path_by_id(tree, node_id):
    """Depth-first search for the first node whose ``id`` equals ``node_id``."""

    def walk(items, prefix):
        for idx, node in enumerate(items):
            if node["id"] == node_id:
                return [*prefix, idx]
            found = walk(node["children"], [*prefix, idx])
            if found is not None:
                return found
        return None

    return walk(tree, [])


# --------------------------------------------------------------------------- #
# selection / path-set utilities
# --------------------------------------------------------------------------- #


def prune_descendants(paths):
    """Remove paths whose ancestor is also in the set.

    Returns unique paths as lists (order unspecified).
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
    """Append a new node ``label`` under ``parent_path``.

    ``parent_path`` of ``[]`` adds at the root level.
    """
    new_node = make_node(label)
    if not parent_path:
        tree.append(new_node)
    else:
        get_node(tree, parent_path)["children"].append(new_node)
    return new_node


def rename_item(tree, path, label):
    """Update the ``label`` of the node at ``path`` (no-op when unchanged)."""
    node = get_node(tree, path)
    if node["label"] != label:
        node["label"] = label


def remove_items(tree, paths):
    """Remove every node referenced by ``paths``.

    Overlapping paths (a parent and a descendant both selected) are
    collapsed first so each subtree is removed at most once.
    """
    pruned = prune_descendants(paths)
    # Sort descending so earlier removals don't invalidate later indices.
    for path in sorted(pruned, reverse=True):
        parent_list, idx = _parent_list_and_index(tree, path)
        parent_list.pop(idx)


def regroup_selection(tree, paths, label="Group"):
    """Wrap the roots of ``paths`` in a new group at the first root's spot.

    Returns the freshly created group, or ``None`` for an empty
    selection.
    """
    roots = sorted(prune_descendants(paths))
    if not roots:
        return None

    # Remember the order in which the user selected the roots.
    ordered_ids = [get_node(tree, p)["id"] for p in roots]
    anchor_parent_list, anchor_idx = _parent_list_and_index(tree, roots[0])

    # Pop roots (descending order) and stash them by id so the group's
    # children can be rebuilt in the original tree order.
    by_id: dict[int, Node] = {}
    for path in sorted(roots, reverse=True):
        parent_list, idx = _parent_list_and_index(tree, path)
        node = parent_list.pop(idx)
        by_id[node["id"]] = node

    group_children = [by_id[i] for i in ordered_ids]
    new_group = make_node(label, children=group_children)

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

    # Filter out cycles: target must not lie inside any source subtree.
    if target_path is not None:
        target_tuple = tuple(target_path)
        sources = [s for s in sources if target_tuple[: len(s)] != tuple(s)]
        if not sources:
            return

    # Capture sources and target by id (id survives the popping below).
    ordered_ids = [get_node(tree, p)["id"] for p in sources]
    target_id = (
        get_node(tree, target_path)["id"]
        if target_path is not None and position != "viewport"
        else None
    )

    # Pop sources (descending) so indices remain stable across the pop.
    by_id: dict[int, Node] = {}
    for path in sorted(sources, reverse=True):
        parent_list, idx = _parent_list_and_index(tree, path)
        node = parent_list.pop(idx)
        by_id[node["id"]] = node

    # Resolve the destination *after* removal, using the target's id
    # because its path may have shifted.
    if position == "viewport" or target_id is None:
        dest_parent, dest_idx = tree, len(tree)
    elif position == "on":
        target_now = get_node(tree, find_path_by_id(tree, target_id))
        dest_parent = target_now["children"]
        dest_idx = len(target_now["children"])
    else:
        new_target_path = find_path_by_id(tree, target_id)
        dest_parent, t_idx = _parent_list_and_index(tree, new_target_path)
        dest_idx = t_idx + (1 if position == "below" else 0)

    for offset, nid in enumerate(ordered_ids):
        dest_parent.insert(dest_idx + offset, by_id[nid])
