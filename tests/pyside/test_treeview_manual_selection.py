import pytest

pytest.importorskip("PySide6")

from observ import reactive
from PySide6 import QtCore, QtWidgets

import collagraph as cg


def test_treeview_manual_selection_preserved_on_shuffle(qtbot, parse_source):
    """
    Test that manual user selection (not bound to template) is preserved
    when the list is shuffled using keyed v-for.
    """
    element, _ = parse_source(
        """
        <treeview>
          <itemmodel>
            <standarditem
              v-for="item in items"
              :key="item['id']"
              :text="item['text']"
            >
            </standarditem>
          </itemmodel>
        </treeview>

        <script>
        import collagraph as cg

        class Element(cg.Component):
            pass
        </script>
        """
    )

    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    state = reactive(
        {
            "items": [
                {"id": 1, "text": "Item 1"},
                {"id": 2, "text": "Item 2"},
                {"id": 3, "text": "Item 3"},
                {"id": 4, "text": "Item 4"},
            ]
        }
    )

    container = renderer.create_element("widget")
    gui.render(element, container, state=state)

    tree_view = None
    model = None

    def find_tree_and_model():
        nonlocal tree_view, model
        tree_view = container.findChild(QtWidgets.QTreeView)
        assert tree_view is not None
        model = tree_view.model()
        assert model is not None
        assert model.rowCount() == 4

    qtbot.waitUntil(find_tree_and_model, timeout=500)

    index = tree_view.model().index(0, 0)
    rect = tree_view.visualRect(index)
    assert rect.isValid() and rect.isEmpty() is False
    click_point = rect.center()
    qtbot.mouseClick(
        tree_view.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=click_point
    )

    new_index = 0

    def check_selection():
        # Check all rows
        texts = []
        selections = []
        for row in range(4):
            index = model.index(row, 0)
            item = model.itemFromIndex(index)

            texts.append(item.text())
            selections.append(tree_view.selectionModel().isSelected(index))

        assert texts == [it["text"] for it in state["items"]], texts
        expected = [False, False, False, False]
        expected[new_index] = True
        assert selections == expected, (selections, expected)

    qtbot.waitUntil(check_selection, timeout=500)

    # Manually select Item 1 (at row 0) using the selection model
    selection_model = tree_view.selectionModel()

    # Verify Item 1 is selected
    def check_item1_selected():
        index = model.index(0, 0)
        item = model.itemFromIndex(index)
        assert item.text() == "Item 1"
        assert selection_model.isSelected(index) is True

    qtbot.waitUntil(check_item1_selected, timeout=500)

    # Shuffle the list to [Item 3, Item 4, Item 1, Item 2]
    state["items"] = [
        state["items"][2],  # Item 3
        state["items"][3],  # Item 4
        state["items"][0],  # Item 1
        state["items"][1],  # Item 2
    ]

    new_index = -1
    for idx, item in enumerate(state["items"]):
        if item["id"] == 1:
            new_index = idx
            break

    assert new_index != -1

    # Wait for reconciliation to complete
    qtbot.wait(200)

    # After shuffling, ONLY Item 1 should still be selected (now at row 2)
    def check_after_shuffle():
        # Check all rows
        texts = []
        selections = []
        for row in range(4):
            index = model.index(row, 0)
            item = model.itemFromIndex(index)

            texts.append(item.text())
            selections.append(selection_model.isSelected(index))

        assert texts == [item["text"] for item in state["items"]], texts
        expected = [False, False, False, False]
        expected[new_index] = True
        assert selections == expected, (selections, expected)

    qtbot.waitUntil(check_after_shuffle, timeout=500)

    assert len(tree_view.selectionModel().selectedIndexes()) == 1


def test_treeview_manual_selection_with_children(qtbot, parse_source):
    """
    Test that manual user selection is preserved when items have children
    and the list is shuffled using keyed v-for.
    """
    element, _ = parse_source(
        """
        <treeview>
          <itemmodel>
            <standarditem
              v-for="item in items"
              :key="item['id']"
              :text="item['text']"
            >
              <standarditem
                v-for="child in item['children']"
                :key="child['id']"
                :text="child['text']"
              />
            </standarditem>
          </itemmodel>
        </treeview>

        <script>
        import collagraph as cg

        class Element(cg.Component):
            pass
        </script>
        """
    )

    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    state = reactive(
        {
            "items": [
                {
                    "id": 1,
                    "text": "Parent 1",
                    "children": [
                        {"id": 11, "text": "Child 1.1"},
                        {"id": 12, "text": "Child 1.2"},
                    ],
                },
                {
                    "id": 2,
                    "text": "Parent 2",
                    "children": [
                        {"id": 21, "text": "Child 2.1"},
                    ],
                },
                {
                    "id": 3,
                    "text": "Parent 3",
                    "children": [
                        {"id": 31, "text": "Child 3.1"},
                        {"id": 32, "text": "Child 3.2"},
                        {"id": 33, "text": "Child 3.3"},
                    ],
                },
            ]
        }
    )

    container = renderer.create_element("widget")
    gui.render(element, container, state=state)

    tree_view = None
    model = None

    def find_tree_and_model():
        nonlocal tree_view, model
        tree_view = container.findChild(QtWidgets.QTreeView)
        assert tree_view is not None
        model = tree_view.model()
        assert model is not None
        assert model.rowCount() == 3

    qtbot.waitUntil(find_tree_and_model, timeout=500)

    # Manually select Parent 2 (at row 1) using mouse click
    parent2_index = model.index(1, 0)
    rect = tree_view.visualRect(parent2_index)
    assert rect.isValid() and not rect.isEmpty()
    click_point = rect.center()
    qtbot.mouseClick(
        tree_view.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=click_point
    )

    selection_model = tree_view.selectionModel()

    # Verify Parent 2 is selected
    def check_parent2_selected():
        index = model.index(1, 0)
        item = model.itemFromIndex(index)
        assert item.text() == "Parent 2"
        assert selection_model.isSelected(index) is True

    qtbot.waitUntil(check_parent2_selected, timeout=500)

    # Shuffle the parent items to [Parent 3, Parent 1, Parent 2]
    state["items"] = [
        state["items"][2],  # Parent 3
        state["items"][0],  # Parent 1
        state["items"][1],  # Parent 2
    ]

    # Wait for reconciliation to complete
    qtbot.wait(200)

    # After shuffling, ONLY Parent 2 should still be selected (now at row 2)
    def check_after_shuffle():
        # Check all parent rows
        for row in range(3):
            index = model.index(row, 0)
            item = model.itemFromIndex(index)

            if item.text() == "Parent 2":
                # Parent 2 should be selected
                assert selection_model.isSelected(index) is True, (
                    f"Parent 2 (now at row {row}) should still be selected"
                )
                # Verify children are intact
                assert item.rowCount() == 1
                assert item.child(0).text() == "Child 2.1"
            else:
                # Other parents should NOT be selected
                assert selection_model.isSelected(index) is False, (
                    f"{item.text()} (at row {row}) should NOT be selected"
                )

        # Verify final order
        assert model.item(0).text() == "Parent 3"
        assert model.item(0).rowCount() == 3  # Has 3 children
        assert model.item(1).text() == "Parent 1"
        assert model.item(1).rowCount() == 2  # Has 2 children
        assert model.item(2).text() == "Parent 2"
        assert model.item(2).rowCount() == 1  # Has 1 child

    qtbot.waitUntil(check_after_shuffle, timeout=500)

    assert len(selection_model.selectedIndexes()) == 1


def test_treeview_manual_selection_child_item(qtbot, parse_source):
    """
    Test that manual selection of a child item is preserved when parent items
    are shuffled using keyed v-for.
    """
    element, _ = parse_source(
        """
        <treeview>
          <itemmodel>
            <standarditem
              v-for="item in items"
              :key="item['id']"
              :text="item['text']"
            >
              <standarditem
                v-for="child in item['children']"
                :key="child['id']"
                :text="child['text']"
              />
            </standarditem>
          </itemmodel>
        </treeview>

        <script>
        import collagraph as cg

        class Element(cg.Component):
            pass
        </script>
        """
    )

    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)

    state = reactive(
        {
            "items": [
                {
                    "id": 1,
                    "text": "Parent 1",
                    "children": [
                        {"id": 11, "text": "Child 1.1"},
                        {"id": 12, "text": "Child 1.2"},
                    ],
                },
                {
                    "id": 2,
                    "text": "Parent 2",
                    "children": [
                        {"id": 21, "text": "Child 2.1"},
                    ],
                },
                {
                    "id": 3,
                    "text": "Parent 3",
                    "children": [
                        {"id": 31, "text": "Child 3.1"},
                        {"id": 32, "text": "Child 3.2"},
                    ],
                },
            ]
        }
    )

    container = renderer.create_element("widget")
    gui.render(element, container, state=state)

    tree_view = None
    model = None

    def find_tree_and_model():
        nonlocal tree_view, model
        tree_view = container.findChild(QtWidgets.QTreeView)
        assert tree_view is not None
        model = tree_view.model()
        assert model is not None
        assert model.rowCount() == 3

    qtbot.waitUntil(find_tree_and_model, timeout=500)

    # Expand Parent 1 to show its children
    parent1_index = model.index(0, 0)
    tree_view.expand(parent1_index)

    # Wait for expansion
    qtbot.wait(100)

    # Manually select Child 1.2 (second child of Parent 1)
    parent1_item = model.item(0)
    child12_item = parent1_item.child(1)  # Child 1.2
    child12_index = model.indexFromItem(child12_item)

    rect = tree_view.visualRect(child12_index)
    assert rect.isValid() and not rect.isEmpty()
    click_point = rect.center()
    qtbot.mouseClick(
        tree_view.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=click_point
    )

    selection_model = tree_view.selectionModel()

    # Verify Child 1.2 is selected
    def check_child_selected():
        parent1_item = model.item(0)
        child12_item = parent1_item.child(1)
        assert child12_item.text() == "Child 1.2"
        child12_index = model.indexFromItem(child12_item)
        assert selection_model.isSelected(child12_index) is True

    qtbot.waitUntil(check_child_selected, timeout=500)

    # Shuffle the parent items to [Parent 3, Parent 1, Parent 2]
    state["items"] = [
        state["items"][2],  # Parent 3
        state["items"][0],  # Parent 1
        state["items"][1],  # Parent 2
    ]

    # Wait for reconciliation to complete
    qtbot.wait(200)

    # After shuffling, ONLY Child 1.2 should still be selected
    # Parent 1 is now at row 1, and Child 1.2 should still be its second child
    def check_after_shuffle():
        # Find Parent 1 (now at row 1)
        parent1_item = None
        for row in range(3):
            item = model.item(row)
            if item.text() == "Parent 1":
                parent1_item = item
                assert row == 1, "Parent 1 should be at row 1 after shuffle"
                break

        assert parent1_item is not None, "Parent 1 should exist"
        assert parent1_item.rowCount() == 2, "Parent 1 should have 2 children"

        # Check that Child 1.2 is still selected
        child12_item = parent1_item.child(1)
        assert child12_item.text() == "Child 1.2"
        child12_index = model.indexFromItem(child12_item)
        assert selection_model.isSelected(child12_index) is True, (
            "Child 1.2 should still be selected after shuffle"
        )

        # Verify no other items are selected
        for row in range(3):
            parent_item = model.item(row)
            parent_index = model.indexFromItem(parent_item)

            if parent_item.text() != "Parent 1":
                # Other parents should not be selected
                assert selection_model.isSelected(parent_index) is False, (
                    f"{parent_item.text()} should not be selected"
                )

            # Check all children of this parent
            for child_row in range(parent_item.rowCount()):
                child_item = parent_item.child(child_row)
                child_index = model.indexFromItem(child_item)

                if child_item.text() == "Child 1.2":
                    # This is the selected child
                    assert selection_model.isSelected(child_index) is True
                else:
                    # Other children should not be selected
                    assert selection_model.isSelected(child_index) is False, (
                        f"{child_item.text()} should not be selected"
                    )

    qtbot.waitUntil(check_after_shuffle, timeout=500)

    assert len(selection_model.selectedIndexes()) == 1
