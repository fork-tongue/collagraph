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
