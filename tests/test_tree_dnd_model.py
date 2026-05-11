"""Unit tests for the pure-Python tree-model logic that powers the
drag-and-drop tree-widget example.

The model operates on plain (nested) Python ``dict`` / ``list``
structures — the same shape the .cgx component stores inside its
reactive state. No Qt or collagraph is involved here.
"""

from examples.pyside.tree_dnd_model import (
    add_item,
    find_path,
    find_path_by_id,
    get_node,
    make_node,
    move_items,
    prune_descendants,
    regroup_selection,
    remove_items,
    rename_item,
)


def _labels(tree):
    """Serialise a tree into nested ``(label, [...])`` tuples."""
    return [(n["label"], _labels(n["children"])) for n in tree]


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
        make_node("A", children=[make_node("A1"), make_node("A2")]),
        make_node(
            "B",
            children=[
                make_node("B1", children=[make_node("B1a")]),
                make_node("B2"),
            ],
        ),
        make_node("C"),
    ]


# --------------------------------------------------------------------------- #
# make_node
# --------------------------------------------------------------------------- #


def test_make_node_defaults_to_expanded():
    n = make_node("x")
    assert n["label"] == "x"
    assert n["expanded"] is True
    assert n["children"] == []
    assert isinstance(n["id"], int)


def test_make_node_ids_are_unique():
    ids = {make_node("x")["id"] for _ in range(20)}
    assert len(ids) == 20


def test_make_node_accepts_expanded_flag():
    assert make_node("x", expanded=False)["expanded"] is False


# --------------------------------------------------------------------------- #
# get_node / find_path / find_path_by_id
# --------------------------------------------------------------------------- #


def test_get_node_root_level():
    tree = _build()
    assert get_node(tree, [0])["label"] == "A"
    assert get_node(tree, [2])["label"] == "C"


def test_get_node_nested():
    tree = _build()
    assert get_node(tree, [1, 0, 0])["label"] == "B1a"


def test_find_path_returns_indices():
    tree = _build()
    b1a = tree[1]["children"][0]["children"][0]
    assert find_path(tree, b1a) == [1, 0, 0]


def test_find_path_returns_none_for_unknown_node():
    tree = _build()
    orphan = make_node("orphan")
    assert find_path(tree, orphan) is None


def test_find_path_by_id():
    tree = _build()
    b1a_id = tree[1]["children"][0]["children"][0]["id"]
    assert find_path_by_id(tree, b1a_id) == [1, 0, 0]


def test_find_path_by_id_returns_none_for_unknown():
    tree = _build()
    assert find_path_by_id(tree, 99999) is None


# --------------------------------------------------------------------------- #
# add_item
# --------------------------------------------------------------------------- #


def test_add_item_to_root():
    tree = _build()
    add_item(tree, [], "D")
    assert [n["label"] for n in tree] == ["A", "B", "C", "D"]


def test_add_item_under_parent():
    tree = _build()
    add_item(tree, [0], "A3")
    assert [n["label"] for n in tree[0]["children"]] == ["A1", "A2", "A3"]


def test_add_item_deeply_nested():
    tree = _build()
    add_item(tree, [1, 0], "B1b")
    assert [n["label"] for n in tree[1]["children"][0]["children"]] == ["B1a", "B1b"]


# --------------------------------------------------------------------------- #
# rename_item
# --------------------------------------------------------------------------- #


def test_rename_item_changes_label():
    tree = _build()
    rename_item(tree, [0], "renamed")
    assert tree[0]["label"] == "renamed"


def test_rename_item_at_deep_path():
    tree = _build()
    rename_item(tree, [1, 0, 0], "deep")
    assert tree[1]["children"][0]["children"][0]["label"] == "deep"


def test_rename_item_noop_when_label_unchanged():
    tree = _build()
    before = tree[0]
    rename_item(tree, [0], "A")
    assert tree[0] is before
    assert tree[0]["label"] == "A"


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
    assert [n["label"] for n in tree] == ["B", "C"]


def test_remove_multiple_disjoint():
    tree = _build()
    remove_items(tree, [[0], [2]])
    assert [n["label"] for n in tree] == ["B"]


def test_remove_nested_item():
    tree = _build()
    remove_items(tree, [[1, 0, 0]])
    assert tree[1]["children"][0]["children"] == []


def test_remove_collapses_overlapping_paths():
    tree = _build()
    remove_items(tree, [[1], [1, 0], [1, 0, 0]])
    assert [n["label"] for n in tree] == ["A", "C"]


def test_remove_keeps_indices_stable_when_processed_in_reverse():
    tree = _build()
    remove_items(tree, [[1], [0]])
    assert [n["label"] for n in tree] == ["C"]


# --------------------------------------------------------------------------- #
# regroup_selection
# --------------------------------------------------------------------------- #


def test_regroup_two_root_siblings_into_new_group():
    tree = _build()
    group = regroup_selection(tree, [[0], [1]], label="Group")

    assert [n["label"] for n in tree] == ["Group", "C"]
    assert group is tree[0]
    assert [n["label"] for n in group["children"]] == ["A", "B"]
    assert [n["label"] for n in group["children"][0]["children"]] == ["A1", "A2"]


def test_regroup_skips_descendants_of_other_selected_items():
    tree = _build()
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
    assert group["label"] == "G"


def test_regroup_keeps_first_root_position_within_parent():
    tree = [
        make_node(
            "root",
            children=[
                make_node("x"),
                make_node("y"),
                make_node("z"),
            ],
        )
    ]
    regroup_selection(tree, [[0, 1], [0, 2]], label="G")
    assert _labels(tree) == [("root", [("x", []), ("G", [("y", []), ("z", [])])])]


def test_regroup_returns_none_for_empty_selection():
    tree = _build()
    assert regroup_selection(tree, [], label="G") is None
    assert [n["label"] for n in tree] == ["A", "B", "C"]


def test_regroup_two_items_from_different_parents_puts_group_at_first():
    tree = _build()
    regroup_selection(tree, [[0, 1], [1, 0]], label="G")

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
    move_items(tree, [[0]], target_path=[2], position="below")
    assert [n["label"] for n in tree] == ["B", "C", "A"]


def test_move_single_item_above_sibling():
    tree = _build()
    move_items(tree, [[2]], target_path=[0], position="above")
    assert [n["label"] for n in tree] == ["C", "A", "B"]


def test_move_item_into_other_item_as_child():
    tree = _build()
    move_items(tree, [[2]], target_path=[0], position="on")
    assert [n["label"] for n in tree] == ["A", "B"]
    assert [n["label"] for n in tree[0]["children"]] == ["A1", "A2", "C"]


def test_move_to_viewport_appends_to_root():
    tree = _build()
    move_items(tree, [[1, 0]], target_path=None, position="viewport")
    assert [n["label"] for n in tree] == ["A", "B", "C", "B1"]
    assert [n["label"] for n in tree[1]["children"]] == ["B2"]


def test_move_refuses_to_drop_into_own_descendant():
    tree = _build()
    snapshot = _labels(tree)
    move_items(tree, [[1]], target_path=[1, 0, 0], position="on")
    assert _labels(tree) == snapshot


def test_move_preserves_relative_order_when_moving_multiple():
    tree = _build()
    move_items(tree, [[0], [2]], target_path=[1], position="on")
    assert [n["label"] for n in tree] == ["B"]
    assert [n["label"] for n in tree[0]["children"]] == ["B1", "B2", "A", "C"]


def test_move_above_target_when_source_precedes_target():
    tree = [make_node("a"), make_node("b"), make_node("c")]
    move_items(tree, [[0]], target_path=[2], position="above")
    assert [n["label"] for n in tree] == ["b", "a", "c"]


def test_move_below_target_when_source_precedes_target():
    tree = [make_node("a"), make_node("b"), make_node("c")]
    move_items(tree, [[0]], target_path=[1], position="below")
    assert [n["label"] for n in tree] == ["b", "a", "c"]


def test_move_descendants_are_pruned_from_source_set():
    tree = _build()
    move_items(tree, [[1], [1, 0]], target_path=[2], position="below")
    assert [n["label"] for n in tree] == ["A", "C", "B"]
    assert [n["label"] for n in tree[2]["children"]] == ["B1", "B2"]


def test_move_does_nothing_when_only_source_is_target_descendant():
    tree = _build()
    snapshot = _labels(tree)
    move_items(tree, [[1, 0]], target_path=[1, 0, 0], position="on")
    assert _labels(tree) == snapshot


def test_move_preserves_node_identity_via_id():
    tree = _build()
    bread_id = tree[2]["id"]
    move_items(tree, [[2]], target_path=[0], position="on")
    # Bread is now the last child of A; its id is unchanged.
    moved = tree[0]["children"][-1]
    assert moved["id"] == bread_id
    assert moved["label"] == "C"


def test_move_preserves_expanded_state_of_moved_node():
    tree = _build()
    tree[2]["expanded"] = False
    move_items(tree, [[2]], target_path=[0], position="on")
    assert tree[0]["children"][-1]["expanded"] is False
