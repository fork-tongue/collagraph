"""Integration tests for the drag-and-drop tree-widget example.

These tests drive ``examples/pyside/tree_dnd_example.cgx`` through its
public state-mutation entry points (the same ones the buttons call) and
through the custom ``itemDropped`` signal, then verify the QTreeWidget
mirrors what the state says it should be.

Screenshots are written under ``tests/pyside/_screenshots/`` so the
example's behaviour can be eyeballed after a run.
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

SCREENSHOT_DIR = Path(__file__).resolve().parent / "_screenshots"


@pytest.fixture
def example_component():
    component_class, _namespace = load(EXAMPLE_PATH)
    return component_class


def _screenshot(widget: QtWidgets.QWidget, name: str) -> Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"{name}.png"
    pixmap = widget.grab()
    assert not pixmap.isNull(), "Failed to grab widget pixmap"
    assert pixmap.save(str(path)), f"Failed to save screenshot to {path}"
    return path


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

    container.resize(520, 520)
    container.show()
    qtbot.waitExposed(container)
    tree_widget.expandAll()
    _screenshot(container, "01_initial")


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

    container.resize(520, 520)
    container.show()
    qtbot.waitExposed(container)
    tree_widget.expandAll()
    _screenshot(container, "02_after_add_root")


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

    container.resize(520, 520)
    container.show()
    qtbot.waitExposed(container)
    tree_widget.expandAll()
    _screenshot(container, "03_after_remove")


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

    container.resize(520, 520)
    container.show()
    qtbot.waitExposed(container)
    tree_widget.expandAll()
    _screenshot(container, "04_after_group")


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

    container.resize(520, 520)
    container.show()
    qtbot.waitExposed(container)
    tree_widget.expandAll()
    _screenshot(container, "05_after_drop_on")


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

    container.resize(520, 520)
    container.show()
    qtbot.waitExposed(container)
    tree_widget.expandAll()
    _screenshot(container, "06_after_drop_above")


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
# combined scenario
# --------------------------------------------------------------------------- #


def test_full_workflow_screenshots(qtbot, example_component):
    """End-to-end: add → group → drop, capturing screenshots at each step."""
    _renderer, _gui, container = _render(example_component)
    container.resize(520, 520)
    container.show()
    qtbot.waitExposed(container)

    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)
    tree_widget.expandAll()
    _screenshot(container, "07_workflow_initial")

    # 1) Add a root item.
    add_root = next(
        b
        for b in container.findChildren(QtWidgets.QPushButton)
        if b.text() == "Add root"
    )
    qtbot.mouseClick(add_root, QtCore.Qt.LeftButton)

    def four_roots():
        assert tree_widget.topLevelItemCount() == 4

    qtbot.waitUntil(four_roots, timeout=1000)
    tree_widget.expandAll()
    _screenshot(container, "07_workflow_after_add")

    # 2) Select the new item and two siblings, then group.
    _select_paths_via_state(container, [[1], [2], [3]])
    group_button = next(
        b for b in container.findChildren(QtWidgets.QPushButton) if b.text() == "Group"
    )

    def group_enabled():
        assert group_button.isEnabled()

    qtbot.waitUntil(group_enabled, timeout=1000)
    qtbot.mouseClick(group_button, QtCore.Qt.LeftButton)

    def two_roots_with_group():
        assert tree_widget.topLevelItemCount() == 2
        assert tree_widget.topLevelItem(1).text(0) == "Group"

    qtbot.waitUntil(two_roots_with_group, timeout=1000)
    tree_widget.expandAll()
    _screenshot(container, "07_workflow_after_group")

    # 3) Drop the new group onto Fruit.
    tree_widget.itemDropped.emit([[1]], [0], "on")

    def group_moved_into_fruit():
        assert tree_widget.topLevelItemCount() == 1
        fruit = tree_widget.topLevelItem(0)
        last_child = fruit.child(fruit.childCount() - 1)
        assert last_child.text(0) == "Group"

    qtbot.waitUntil(group_moved_into_fruit, timeout=1500)
    tree_widget.expandAll()
    _screenshot(container, "07_workflow_after_drop")


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
    """Collapsing an item via Qt updates ``state[tree][i]['expanded']``."""
    _renderer, gui, container = _render(example_component)

    tree_widget = None

    def find():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget, "tree")
        assert tree_widget is not None and tree_widget.topLevelItemCount() == 3

    qtbot.waitUntil(find, timeout=1000)

    fruit_item = tree_widget.topLevelItem(0)
    assert fruit_item.text(0) == "Fruit"

    # Simulate the user collapsing the first row.
    fruit_item.setExpanded(False)

    component = gui.fragment.component

    def state_reflects_collapse():
        assert component.state["tree"][0]["expanded"] is False

    qtbot.waitUntil(state_reflects_collapse, timeout=1000)


def test_state_collapse_propagates_to_widget(qtbot, example_component):
    """Writing ``expanded = False`` into state collapses the item."""
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

    component.state["tree"][0]["expanded"] = False
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

    container.resize(520, 560)
    container.show()
    qtbot.waitExposed(container)
    _screenshot(container, "08_reorder_keeps_expansion")


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

    container.resize(520, 560)
    container.show()
    qtbot.waitExposed(container)
    _screenshot(container, "09_after_rename")
