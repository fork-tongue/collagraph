"""Unit tests for the pure-Python tree-model logic that powers the
drag-and-drop tree-widget example.

The model is exercised here without Qt or collagraph involved so that
the operations (add / remove / regroup / move) can be developed and
verified in isolation. The same module is consumed by the .cgx example
under ``examples/pyside/tree_dnd_example.cgx``.
"""

from examples.pyside.tree_dnd_model import (
    TreeNode,
    add_item,
    find_path,
    get_node,
    move_items,
    prune_descendants,
    regroup_selection,
    remove_items,
)


def _labels(tree):
    """Recursively serialise a tree of TreeNode into nested lists of labels."""
    return [(n.label, _labels(n.children)) for n in tree]


def _build():
    """Build a small fixture tree::

        A
        ├── A1
        └── A2
        B
        ├── B1
        │   └── B1a
        └── B2
        C
    """
    return [
        TreeNode("A", children=[TreeNode("A1"), TreeNode("A2")]),
        TreeNode(
            "B",
            children=[
                TreeNode("B1", children=[TreeNode("B1a")]),
                TreeNode("B2"),
            ],
        ),
        TreeNode("C"),
    ]


# --------------------------------------------------------------------------- #
# get_node / find_path
# --------------------------------------------------------------------------- #


def test_get_node_root_level():
    tree = _build()
    assert get_node(tree, [0]).label == "A"
    assert get_node(tree, [2]).label == "C"


def test_get_node_nested():
    tree = _build()
    assert get_node(tree, [1, 0, 0]).label == "B1a"


def test_find_path_returns_indices():
    tree = _build()
    b1a = tree[1].children[0].children[0]
    assert find_path(tree, b1a) == [1, 0, 0]


def test_find_path_returns_none_for_unknown_node():
    tree = _build()
    orphan = TreeNode("orphan")
    assert find_path(tree, orphan) is None


# --------------------------------------------------------------------------- #
# add_item
# --------------------------------------------------------------------------- #


def test_add_item_to_root():
    tree = _build()
    add_item(tree, [], "D")
    assert [n.label for n in tree] == ["A", "B", "C", "D"]


def test_add_item_under_parent():
    tree = _build()
    add_item(tree, [0], "A3")
    assert [n.label for n in tree[0].children] == ["A1", "A2", "A3"]


def test_add_item_deeply_nested():
    tree = _build()
    add_item(tree, [1, 0], "B1b")
    assert [n.label for n in tree[1].children[0].children] == ["B1a", "B1b"]


# --------------------------------------------------------------------------- #
# prune_descendants
# --------------------------------------------------------------------------- #


def test_prune_descendants_keeps_roots():
    paths = [[0], [0, 0], [0, 1], [1]]
    assert sorted(prune_descendants(paths)) == [[0], [1]]


def test_prune_descendants_keeps_disjoint_paths():
    paths = [[0, 0], [1, 0, 0], [2]]
    assert sorted(prune_descendants(paths)) == [[0, 0], [1, 0, 0], [2]]


def test_prune_descendants_handles_duplicates():
    paths = [[1], [1], [1, 0]]
    assert sorted(prune_descendants(paths)) == [[1]]


# --------------------------------------------------------------------------- #
# remove_items
# --------------------------------------------------------------------------- #


def test_remove_single_root():
    tree = _build()
    remove_items(tree, [[0]])
    assert [n.label for n in tree] == ["B", "C"]


def test_remove_multiple_disjoint():
    tree = _build()
    remove_items(tree, [[0], [2]])
    assert [n.label for n in tree] == ["B"]


def test_remove_nested_item():
    tree = _build()
    remove_items(tree, [[1, 0, 0]])
    assert tree[1].children[0].children == []


def test_remove_collapses_overlapping_paths():
    # Selecting a parent and a child should not crash; only the parent
    # is removed.
    tree = _build()
    remove_items(tree, [[1], [1, 0], [1, 0, 0]])
    assert [n.label for n in tree] == ["A", "C"]


def test_remove_keeps_indices_stable_when_processed_in_reverse():
    tree = _build()
    # Remove A and B together; expect just C left.
    remove_items(tree, [[1], [0]])
    assert [n.label for n in tree] == ["C"]


# --------------------------------------------------------------------------- #
# regroup_selection
# --------------------------------------------------------------------------- #


def test_regroup_two_root_siblings_into_new_group():
    tree = _build()
    group = regroup_selection(tree, [[0], [1]], label="Group")

    assert [n.label for n in tree] == ["Group", "C"]
    assert group is tree[0]
    assert [n.label for n in group.children] == ["A", "B"]
    # And the children of A / B are preserved
    assert [n.label for n in group.children[0].children] == ["A1", "A2"]


def test_regroup_skips_descendants_of_other_selected_items():
    tree = _build()
    # Selecting B and B1 means only B is regrouped.
    group = regroup_selection(tree, [[1], [1, 0]], label="G")
    assert _labels(tree) == [
        ("A", [("A1", []), ("A2", [])]),
        (
            "G",
            [
                ("B", [("B1", [("B1a", [])]), ("B2", [])]),
            ],
        ),
        ("C", []),
    ]
    assert group.label == "G"


def test_regroup_keeps_first_root_position_within_parent():
    # Build a tree where the selected items live inside the same parent.
    tree = [
        TreeNode(
            "root",
            children=[
                TreeNode("x"),
                TreeNode("y"),
                TreeNode("z"),
            ],
        )
    ]
    regroup_selection(tree, [[0, 1], [0, 2]], label="G")
    # x stays, then the new group containing y and z.
    assert _labels(tree) == [
        ("root", [("x", []), ("G", [("y", []), ("z", [])])])
    ]


def test_regroup_returns_none_for_empty_selection():
    tree = _build()
    assert regroup_selection(tree, [], label="G") is None
    # Tree unchanged.
    assert [n.label for n in tree] == ["A", "B", "C"]


def test_regroup_two_items_from_different_parents_puts_group_at_first():
    tree = _build()
    # Select A2 (path [0,1]) and B1 (path [1,0]).
    regroup_selection(tree, [[0, 1], [1, 0]], label="G")

    # A2 was at [0,1]. The new group should appear at [0,1] (replacing
    # A2's original spot), and contain A2 + B1.
    assert _labels(tree) == [
        (
            "A",
            [
                ("A1", []),
                ("G", [("A2", []), ("B1", [("B1a", [])])]),
            ],
        ),
        ("B", [("B2", [])]),
        ("C", []),
    ]


# --------------------------------------------------------------------------- #
# move_items
# --------------------------------------------------------------------------- #


def test_move_single_item_below_sibling():
    tree = _build()
    # Move A below C.
    move_items(tree, [[0]], target_path=[2], position="below")
    assert [n.label for n in tree] == ["B", "C", "A"]


def test_move_single_item_above_sibling():
    tree = _build()
    move_items(tree, [[2]], target_path=[0], position="above")
    assert [n.label for n in tree] == ["C", "A", "B"]


def test_move_item_into_other_item_as_child():
    tree = _build()
    # Drop C onto A (position "on") -> C becomes last child of A.
    move_items(tree, [[2]], target_path=[0], position="on")
    assert [n.label for n in tree] == ["A", "B"]
    assert [n.label for n in tree[0].children] == ["A1", "A2", "C"]


def test_move_to_viewport_appends_to_root():
    # Build a tree with a nested item to verify it bubbles up.
    tree = _build()
    move_items(tree, [[1, 0]], target_path=None, position="viewport")
    # B1 was removed from B and appended at root.
    assert [n.label for n in tree] == ["A", "B", "C", "B1"]
    assert [n.label for n in tree[1].children] == ["B2"]


def test_move_refuses_to_drop_into_own_descendant():
    tree = _build()
    # Try to drop B onto B1a (cycle). Tree should be unchanged.
    snapshot = _labels(tree)
    move_items(tree, [[1]], target_path=[1, 0, 0], position="on")
    assert _labels(tree) == snapshot


def test_move_preserves_relative_order_when_moving_multiple():
    tree = _build()
    # Move A and C onto B.
    move_items(tree, [[0], [2]], target_path=[1], position="on")
    assert [n.label for n in tree] == ["B"]
    # A first, then C as the last children of B.
    assert [n.label for n in tree[0].children] == ["B1", "B2", "A", "C"]


def test_move_above_target_when_source_precedes_target():
    # Source comes before target in the same parent — index needs to
    # account for the removal.
    tree = [
        TreeNode("a"),
        TreeNode("b"),
        TreeNode("c"),
    ]
    move_items(tree, [[0]], target_path=[2], position="above")
    # a is removed, then re-inserted just before c. Result: b, a, c.
    assert [n.label for n in tree] == ["b", "a", "c"]


def test_move_below_target_when_source_precedes_target():
    tree = [
        TreeNode("a"),
        TreeNode("b"),
        TreeNode("c"),
    ]
    move_items(tree, [[0]], target_path=[1], position="below")
    # a removed, re-inserted just after b -> b, a, c.
    assert [n.label for n in tree] == ["b", "a", "c"]


def test_move_descendants_are_pruned_from_source_set():
    tree = _build()
    # Selecting B and B1: only B should actually move.
    move_items(tree, [[1], [1, 0]], target_path=[2], position="below")
    assert [n.label for n in tree] == ["A", "C", "B"]
    # B's structure is intact.
    assert [n.label for n in tree[2].children] == ["B1", "B2"]


def test_move_does_nothing_when_only_source_is_target_descendant():
    tree = _build()
    snapshot = _labels(tree)
    # Try to move B1 onto B1a (which is B1's child)
    move_items(tree, [[1, 0]], target_path=[1, 0, 0], position="on")
    assert _labels(tree) == snapshot
