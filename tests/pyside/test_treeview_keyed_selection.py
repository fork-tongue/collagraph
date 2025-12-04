import pytest

pytest.importorskip("PySide6")

from observ import reactive
from PySide6 import QtWidgets

import collagraph as cg


def test_treeview_keyed_vfor_with_selection(qtbot, parse_source):
    """
    Test that tree view items with keyed v-for maintain correct selection
    when list changes.
    """
    element, _ = parse_source(
        """
        <treeview>
          <itemmodel>
            <standarditem
              v-for="item in items"
              :key="item['id']"
              :selected="item['selected']"
              :text="item['name']"
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
                {"id": "a", "name": "Item A", "selected": True},
                {"id": "b", "name": "Item B", "selected": False},
                {"id": "c", "name": "Item C", "selected": False},
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

    # Verify initial state
    def check_initial():
        selection_model = tree_view.selectionModel()
        index_a = model.index(0, 0)
        index_b = model.index(1, 0)
        index_c = model.index(2, 0)

        item_a = model.itemFromIndex(index_a)
        item_b = model.itemFromIndex(index_b)
        item_c = model.itemFromIndex(index_c)

        assert item_a.text() == "Item A"
        assert selection_model.isSelected(index_a) is True
        assert item_b.text() == "Item B"
        assert selection_model.isSelected(index_b) is False
        assert item_c.text() == "Item C"
        assert selection_model.isSelected(index_c) is False

    qtbot.waitUntil(check_initial, timeout=500)

    # Reorder the list - move Item A to the end
    state["items"] = [
        state["items"][1],  # B
        state["items"][2],  # C
        state["items"][0],  # A
    ]

    # Wait for reconciliation to complete
    qtbot.wait(200)

    # After reordering, Item A should still be selected (it's now at index 2)
    def check_after_reorder():
        selection_model = tree_view.selectionModel()
        index_b = model.index(0, 0)
        index_c = model.index(1, 0)
        index_a = model.index(2, 0)

        item_b = model.itemFromIndex(index_b)
        item_c = model.itemFromIndex(index_c)
        item_a = model.itemFromIndex(index_a)

        assert item_b.text() == "Item B"
        assert selection_model.isSelected(index_b) is False, (
            "Item B should not be selected"
        )
        assert item_c.text() == "Item C"
        assert selection_model.isSelected(index_c) is False, (
            "Item C should not be selected"
        )
        assert item_a.text() == "Item A"
        assert selection_model.isSelected(index_a) is True, (
            "Item A should still be selected after reorder"
        )

    qtbot.waitUntil(check_after_reorder, timeout=500)


def test_treeview_keyed_vfor_with_expanded(qtbot, parse_source):
    """Test that expanded state works correctly with keyed v-for and reordering."""
    element, _ = parse_source(
        """
        <treeview>
          <itemmodel>
            <standarditem
              v-for="item in items"
              :key="item['id']"
              :selected="item['selected']"
              :expanded="item['expanded']"
              :text="item['name']"
            >
              <standarditem :text="'Child of ' + item['name']">
              </standarditem>
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
                {"id": "a", "name": "Item A", "selected": True, "expanded": True},
                {"id": "b", "name": "Item B", "selected": False, "expanded": False},
                {"id": "c", "name": "Item C", "selected": False, "expanded": True},
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

    # Verify initial state
    def check_initial():
        selection_model = tree_view.selectionModel()
        index_a = model.index(0, 0)
        index_b = model.index(1, 0)
        index_c = model.index(2, 0)

        item_a = model.itemFromIndex(index_a)
        item_b = model.itemFromIndex(index_b)
        item_c = model.itemFromIndex(index_c)

        assert item_a.text() == "Item A"
        assert selection_model.isSelected(index_a) is True
        assert tree_view.isExpanded(index_a) is True
        assert item_b.text() == "Item B"
        assert selection_model.isSelected(index_b) is False
        assert tree_view.isExpanded(index_b) is False
        assert item_c.text() == "Item C"
        assert selection_model.isSelected(index_c) is False
        assert tree_view.isExpanded(index_c) is True

    qtbot.waitUntil(check_initial, timeout=500)

    # Reverse the order
    state["items"].reverse()

    # Wait for reconciliation to complete
    qtbot.wait(200)

    # After reversing, each item should maintain its selection and expanded state
    def check_after_reverse():
        selection_model = tree_view.selectionModel()
        index_c = model.index(0, 0)
        index_b = model.index(1, 0)
        index_a = model.index(2, 0)

        item_c = model.itemFromIndex(index_c)
        item_b = model.itemFromIndex(index_b)
        item_a = model.itemFromIndex(index_a)

        assert item_c.text() == "Item C"
        assert selection_model.isSelected(index_c) is False, (
            "Item C should not be selected"
        )
        assert tree_view.isExpanded(index_c) is True, "Item C should be expanded"

        assert item_b.text() == "Item B"
        assert selection_model.isSelected(index_b) is False, (
            "Item B should not be selected"
        )
        assert tree_view.isExpanded(index_b) is False, "Item B should not be expanded"

        assert item_a.text() == "Item A"
        assert selection_model.isSelected(index_a) is True, (
            "Item A should still be selected"
        )
        assert tree_view.isExpanded(index_a) is True, "Item A should still be expanded"

    qtbot.waitUntil(check_after_reverse, timeout=500)
