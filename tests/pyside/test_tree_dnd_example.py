"""Integration tests for the drag-and-drop tree-widget example.

These tests drive ``examples/pyside/tree_dnd_example.cgx`` through its
public state-mutation entry points (the same ones the buttons call) and
through the custom ``itemDropped`` signal, then verify the QTreeWidget
mirrors what the state says it should be.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6 import QtCore, QtWidgets

import collagraph as cg
from collagraph.sfc import load

EXAMPLE_PATH = (
    Path(__file__).resolve().parents[2] / "examples" / "pyside" / "tree_dnd_example.cgx"
)


@pytest.fixture
def example_component():
    component_class, _namespace = load(EXAMPLE_PATH)
    return component_class


def _labels_in_tree(tree_widget: QtWidgets.QTreeWidget) -> list:
    """Snapshot QTreeWidget contents as nested ``(label, [...])`` tuples."""

    def walk(item: QtWidgets.QTreeWidgetItem):
        return [
            (item.child(i).text(0), walk(item.child(i)))
            for i in range(item.childCount())
        ]

    return [
        (tree_widget.topLevelItem(i).text(0), walk(tree_widget.topLevelItem(i)))
        for i in range(tree_widget.topLevelItemCount())
    ]


def _flat_labels(tree_widget: QtWidgets.QTreeWidget) -> list[str]:
    out: list[str] = []

    def walk(item):
        out.append(item.text(0))
        for i in range(item.childCount()):
            walk(item.child(i))

    for i in range(tree_widget.topLevelItemCount()):
        walk(tree_widget.topLevelItem(i))
    return out


def _render(example_component):
    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)
    container = renderer.create_element("widget")
    gui.render(example_component, container)
    return renderer, gui, container


def _select_paths_via_state(container, paths):
    """Force-select items by writing through the component's state.

    Tests use this instead of clicking because pytest-qt synthetic
    clicks make the QTreeWidget scroll-to-item then deliver focus
    asynchronously, which races with our reactive scheduler.
    """
    tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
    tree_widget.clearSelection()
    for path in paths:
        item = tree_widget.topLevelItem(path[0])
        for idx in path[1:]:
            item = item.child(idx)
        item.setSelected(True)


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #


def test_example_renders_initial_tree(qtbot, example_component):
    """The example renders its seed tree exactly once on mount."""
    _renderer, _gui, container = _render(example_component)

    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None
        # 3 top-level items in the seed tree.
        assert tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)

    def check_structure():
        labels = _labels_in_tree(tree_widget)
        assert labels == [
            (
                "Fruit",
                [
                    ("Apple", []),
                    ("Banana", []),
                    (
                        "Berries",
                        [("Strawberry", []), ("Blueberry", [])],
                    ),
                ],
            ),
            ("Vegetables", [("Carrot", []), ("Potato", [])]),
            ("Bread", []),
        ]

    qtbot.waitUntil(check_structure, timeout=1000)


# --------------------------------------------------------------------------- #
# add / remove
# --------------------------------------------------------------------------- #


def test_add_root_item(qtbot, example_component):
    _renderer, _gui, container = _render(example_component)
    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)

    add_root_button = next(
        b
        for b in container.findChildren(QtWidgets.QPushButton)
        if b.text() == "Add root"
    )
    qtbot.mouseClick(add_root_button, QtCore.Qt.LeftButton)

    def check_added():
        assert tree_widget.topLevelItemCount() == 4
        assert tree_widget.topLevelItem(3).text(0) == "New item"

    qtbot.waitUntil(check_added, timeout=1000)


def test_remove_selected_item(qtbot, example_component):
    _renderer, _gui, container = _render(example_component)
    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)

    # Select "Bread" (top-level index 2).
    _select_paths_via_state(container, [[2]])

    remove_button = next(
        b for b in container.findChildren(QtWidgets.QPushButton) if b.text() == "Remove"
    )

    def button_enabled():
        assert remove_button.isEnabled()

    qtbot.waitUntil(button_enabled, timeout=1000)
    qtbot.mouseClick(remove_button, QtCore.Qt.LeftButton)

    def check_removed():
        assert tree_widget.topLevelItemCount() == 2
        labels = [
            tree_widget.topLevelItem(i).text(0)
            for i in range(tree_widget.topLevelItemCount())
        ]
        assert labels == ["Fruit", "Vegetables"]

    qtbot.waitUntil(check_removed, timeout=1000)


# --------------------------------------------------------------------------- #
# regroup
# --------------------------------------------------------------------------- #


def test_group_selection_creates_new_group(qtbot, example_component):
    _renderer, _gui, container = _render(example_component)
    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)
    tree_widget.expandAll()

    # Select "Vegetables" and "Bread" at the root level.
    _select_paths_via_state(container, [[1], [2]])

    group_button = next(
        b for b in container.findChildren(QtWidgets.QPushButton) if b.text() == "Group"
    )

    def group_enabled():
        assert group_button.isEnabled()

    qtbot.waitUntil(group_enabled, timeout=1000)
    qtbot.mouseClick(group_button, QtCore.Qt.LeftButton)

    def check_grouped():
        # Top level: Fruit, Group(Vegetables, Bread).
        assert tree_widget.topLevelItemCount() == 2
        labels = [
            tree_widget.topLevelItem(i).text(0)
            for i in range(tree_widget.topLevelItemCount())
        ]
        assert labels == ["Fruit", "Group"]
        group_item = tree_widget.topLevelItem(1)
        child_labels = [
            group_item.child(i).text(0) for i in range(group_item.childCount())
        ]
        assert child_labels == ["Vegetables", "Bread"]

    qtbot.waitUntil(check_grouped, timeout=1000)


# --------------------------------------------------------------------------- #
# drag-and-drop
# --------------------------------------------------------------------------- #


def test_drop_signal_moves_item_into_target(qtbot, example_component):
    """Firing ``itemDropped`` translates into a state-driven tree change."""
    _renderer, _gui, container = _render(example_component)
    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)

    # Pretend the user dropped "Bread" (root index 2) onto "Fruit"
    # (root index 0). Equivalent to position == "on".
    tree_widget.itemDropped.emit([[2]], [0], "on")

    def check_moved():
        # Bread should now be a child of Fruit; only 2 root items left.
        assert tree_widget.topLevelItemCount() == 2
        fruit = tree_widget.topLevelItem(0)
        assert fruit.text(0) == "Fruit"
        # Fruit had 3 children, now 4 with Bread tacked on the end.
        child_labels = [fruit.child(i).text(0) for i in range(fruit.childCount())]
        assert child_labels == ["Apple", "Banana", "Berries", "Bread"]

    qtbot.waitUntil(check_moved, timeout=1000)


def test_drop_signal_reorders_within_root(qtbot, example_component):
    _renderer, _gui, container = _render(example_component)
    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)

    # Drop "Bread" above "Fruit" -> reorder root to Bread, Fruit, Vegetables.
    tree_widget.itemDropped.emit([[2]], [0], "above")

    def check_reordered():
        labels = [
            tree_widget.topLevelItem(i).text(0)
            for i in range(tree_widget.topLevelItemCount())
        ]
        assert labels == ["Bread", "Fruit", "Vegetables"]

    qtbot.waitUntil(check_reordered, timeout=1000)


def test_drop_preserves_selection(qtbot, example_component):
    """Selection should follow items across a move."""
    _renderer, gui, container = _render(example_component)
    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)
    component = gui.fragment.component

    # Select "Bread" (root index 2) and drop it onto "Fruit" (root index 0).
    bread_id = component.state["tree"][2]["id"]
    _select_paths_via_state(container, [[2]])

    def selection_visible_in_state():
        assert component.state["selected_ids"] == [bread_id]

    qtbot.waitUntil(selection_visible_in_state, timeout=1000)

    tree_widget.itemDropped.emit([[2]], [0], "on")

    def bread_still_selected_at_new_position():
        # Tree should have 2 roots now; Bread is the last child of Fruit.
        assert tree_widget.topLevelItemCount() == 2
        fruit = tree_widget.topLevelItem(0)
        moved = fruit.child(fruit.childCount() - 1)
        assert moved.text(0) == "Bread"
        assert moved.isSelected() is True
        # State agrees.
        assert component.state["selected_ids"] == [bread_id]
        assert component.state["selected_paths"] == [[0, 3]]

    qtbot.waitUntil(bread_still_selected_at_new_position, timeout=1500)


def test_chained_drop_within_same_parent_preserves_selection(qtbot, example_component):
    """Two drops in a row should both keep the moved item selected.

    Regression for the case where Bread is first dropped onto Fruit
    (becoming Fruit's last child) and then reordered above Apple — an
    in-place reorder inside Fruit. Without snapshotting the item's
    ``isSelected`` bit across the renderer's remove/insert pair, the
    selection vanished on the second drop.
    """
    _renderer, gui, container = _render(example_component)
    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)
    component = gui.fragment.component
    bread_id = component.state["tree"][2]["id"]

    _select_paths_via_state(container, [[2]])
    qtbot.waitUntil(lambda: component.state["selected_ids"] == [bread_id], timeout=1000)

    # Step 1: drop Bread onto Fruit (Bread becomes the last child).
    tree_widget.itemDropped.emit([[2]], [0], "on")

    def step1_landed():
        fruit = tree_widget.topLevelItem(0)
        assert fruit.childCount() == 4
        assert fruit.child(3).text(0) == "Bread"
        assert fruit.child(3).isSelected() is True
        assert component.state["selected_paths"] == [[0, 3]]

    qtbot.waitUntil(step1_landed, timeout=1500)

    # Step 2: drop Bread above Apple (in-place reorder inside Fruit).
    tree_widget.itemDropped.emit([[0, 3]], [0, 0], "above")

    def step2_landed():
        fruit = tree_widget.topLevelItem(0)
        labels = [fruit.child(i).text(0) for i in range(fruit.childCount())]
        assert labels == ["Bread", "Apple", "Banana", "Berries"]
        # Selection must follow Bread into its new spot.
        assert fruit.child(0).isSelected() is True
        assert component.state["selected_ids"] == [bread_id]
        assert component.state["selected_paths"] == [[0, 0]]

    qtbot.waitUntil(step2_landed, timeout=1500)


def test_reorder_preserves_selection(qtbot, example_component):
    """In-place reorder via drag should also keep the selection."""
    _renderer, gui, container = _render(example_component)
    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)
    component = gui.fragment.component

    bread_id = component.state["tree"][2]["id"]
    _select_paths_via_state(container, [[2]])
    qtbot.waitUntil(lambda: component.state["selected_ids"] == [bread_id], timeout=1000)

    # Drop Bread above Fruit: root order becomes Bread, Fruit, Vegetables.
    tree_widget.itemDropped.emit([[2]], [0], "above")

    def reordered_with_selection():
        labels = [
            tree_widget.topLevelItem(i).text(0)
            for i in range(tree_widget.topLevelItemCount())
        ]
        assert labels == ["Bread", "Fruit", "Vegetables"]
        assert tree_widget.topLevelItem(0).isSelected() is True
        assert component.state["selected_ids"] == [bread_id]
        assert component.state["selected_paths"] == [[0]]

    qtbot.waitUntil(reordered_with_selection, timeout=1500)


def test_drop_into_own_descendant_is_a_noop(qtbot, example_component):
    _renderer, _gui, container = _render(example_component)
    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)

    before = _flat_labels(tree_widget)

    # Try to drop "Fruit" (path [0]) onto "Apple" ([0, 0]) - cycle.
    tree_widget.itemDropped.emit([[0]], [0, 0], "on")

    # Give the scheduler a beat to (not) do anything.
    qtbot.wait(50)

    def unchanged():
        assert _flat_labels(tree_widget) == before

    qtbot.waitUntil(unchanged, timeout=1000)


# --------------------------------------------------------------------------- #
# expansion state
# --------------------------------------------------------------------------- #


def test_initial_state_reflects_expanded_flags(qtbot, example_component):
    """``expanded`` defaults to True so the seed tree mounts open."""
    _renderer, _gui, container = _render(example_component)

    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)

    def all_expanded():
        for i in range(tree_widget.topLevelItemCount()):
            item = tree_widget.topLevelItem(i)
            # Items without children report False, so only check the ones that do.
            if item.childCount() > 0:
                assert item.isExpanded(), f"item {item.text(0)} should be expanded"

    qtbot.waitUntil(all_expanded, timeout=1000)


def test_user_collapse_writes_back_to_state(qtbot, example_component):
    """Collapsing an item via Qt removes its id from ``expanded_ids``."""
    _renderer, gui, container = _render(example_component)

    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)

    fruit_item = tree_widget.topLevelItem(0)
    assert fruit_item.text(0) == "Fruit"

    component = gui.fragment.component
    fruit_id = component.state["tree"][0]["id"]
    # Fruit was seeded as expanded.
    assert fruit_id in component.state["expanded_ids"]

    # Simulate the user collapsing the first row.
    fruit_item.setExpanded(False)

    def state_reflects_collapse():
        assert fruit_id not in component.state["expanded_ids"]

    qtbot.waitUntil(state_reflects_collapse, timeout=1000)


def test_state_collapse_propagates_to_widget(qtbot, example_component):
    """Removing an id from ``expanded_ids`` collapses the matching item."""
    _renderer, gui, container = _render(example_component)

    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)
    component = gui.fragment.component

    fruit_item = tree_widget.topLevelItem(0)
    qtbot.waitUntil(lambda: fruit_item.isExpanded() is True, timeout=1000)

    fruit_id = component.state["tree"][0]["id"]
    component.state["expanded_ids"].remove(fruit_id)
    qtbot.waitUntil(lambda: fruit_item.isExpanded() is False, timeout=1000)


def test_expansion_survives_reorder(qtbot, example_component):
    """Reordering must not collapse the expanded subtree on the moved item.

    Without the renderer's expansion-snapshot, Qt's ``removeChild`` would
    reset ``isExpanded()`` for the subtree being moved.
    """
    _renderer, _gui, container = _render(example_component)

    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)

    # Sanity: Fruit is expanded after initial mount.
    def fruit_expanded():
        assert tree_widget.topLevelItem(0).isExpanded() is True

    qtbot.waitUntil(fruit_expanded, timeout=1000)

    # Move Bread above Fruit; Fruit shifts from index 0 to index 1.
    tree_widget.itemDropped.emit([[2]], [0], "above")

    def reordered_and_still_expanded():
        labels = [
            tree_widget.topLevelItem(i).text(0)
            for i in range(tree_widget.topLevelItemCount())
        ]
        assert labels == ["Bread", "Fruit", "Vegetables"]
        # Fruit (now at index 1) should still be expanded.
        assert tree_widget.topLevelItem(1).isExpanded() is True
        # Vegetables (now at index 2) should still be expanded.
        assert tree_widget.topLevelItem(2).isExpanded() is True

    qtbot.waitUntil(reordered_and_still_expanded, timeout=1500)


# --------------------------------------------------------------------------- #
# rename
# --------------------------------------------------------------------------- #


def test_rename_via_state_updates_widget(qtbot, example_component):
    _renderer, gui, container = _render(example_component)

    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)
    component = gui.fragment.component

    component.state["tree"][0]["label"] = "Produce"

    def widget_reflects_rename():
        assert tree_widget.topLevelItem(0).text(0) == "Produce"

    qtbot.waitUntil(widget_reflects_rename, timeout=1000)


def test_user_edit_writes_back_to_state(qtbot, example_component):
    """Simulate Qt firing ``itemChanged`` after the user edits the text."""
    _renderer, gui, container = _render(example_component)

    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)
    component = gui.fragment.component

    apple_item = tree_widget.topLevelItem(0).child(0)
    assert apple_item.text(0) == "Apple"

    # First a double-click puts the item into edit mode...
    tree_widget.itemDoubleClicked.emit(apple_item, 0)

    def is_editable():
        from PySide6 import QtCore as _QtCore

        assert bool(apple_item.flags() & _QtCore.Qt.ItemIsEditable)

    qtbot.waitUntil(is_editable, timeout=1000)

    # ...then the user types and Qt commits, which fires itemChanged.
    apple_item.setText(0, "Granny Smith")

    def state_reflects_rename():
        assert component.state["tree"][0]["children"][0]["label"] == "Granny Smith"

    qtbot.waitUntil(state_reflects_rename, timeout=1000)
