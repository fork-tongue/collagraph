import pytest

pytest.importorskip("PySide6")

from observ import reactive
from PySide6 import QtWidgets
from PySide6.QtCore import QItemSelectionModel

import collagraph as cg


def test_treeview_keyed_reorder_preserves_bound_selection_and_expanded(
    qtbot, parse_source
):
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
              <standarditem :text="'Child of ' + item['name']" />
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
                {
                    "id": "b",
                    "name": "Item B",
                    "selected": False,
                    "expanded": False,
                },
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

    state["items"] = [state["items"][2], state["items"][1], state["items"][0]]

    qtbot.wait(200)

    def check_after_reorder():
        selection_model = tree_view.selectionModel()

        index_c = model.index(0, 0)
        index_b = model.index(1, 0)
        index_a = model.index(2, 0)

        assert model.itemFromIndex(index_c).text() == "Item C"
        assert selection_model.isSelected(index_c) is False
        assert tree_view.isExpanded(index_c) is True

        assert model.itemFromIndex(index_b).text() == "Item B"
        assert selection_model.isSelected(index_b) is False
        assert tree_view.isExpanded(index_b) is False

        assert model.itemFromIndex(index_a).text() == "Item A"
        assert selection_model.isSelected(index_a) is True
        assert tree_view.isExpanded(index_a) is True

    qtbot.waitUntil(check_after_reorder, timeout=1000)


def test_treeview_keyed_reorder_preserves_manual_parent_selection(qtbot, parse_source):
    element, _ = parse_source(
        """
        <treeview>
          <itemmodel>
            <standarditem
              v-for="item in items"
              :key="item['id']"
              :text="item['text']"
            />
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

    selection_model = tree_view.selectionModel()
    selected_index = model.index(0, 0)
    selection_model.select(
        selected_index,
        QItemSelectionModel.SelectionFlag.Select
        | QItemSelectionModel.SelectionFlag.Rows,
    )

    qtbot.waitUntil(lambda: selection_model.isSelected(model.index(0, 0)), timeout=500)

    state["items"] = [
        state["items"][2],
        state["items"][3],
        state["items"][0],
        state["items"][1],
    ]

    qtbot.wait(200)

    def check_after_reorder():
        assert model.item(0).text() == "Item 3"
        assert model.item(1).text() == "Item 4"
        assert model.item(2).text() == "Item 1"
        assert model.item(3).text() == "Item 2"

        new_index = model.index(2, 0)
        assert selection_model.isSelected(new_index) is True
        assert len(selection_model.selectedRows()) == 1

    qtbot.waitUntil(check_after_reorder, timeout=1000)


def test_treeview_keyed_reorder_preserves_manual_child_selection(qtbot, parse_source):
    element, _ = parse_source(
        """
        <treeview>
          <itemmodel>
            <standarditem
              v-for="item in items"
              :key="item['id']"
              :text="item['text']"
              :expanded="item['expanded']"
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
                    "expanded": True,
                    "children": [
                        {"id": 11, "text": "Child 1.1"},
                        {"id": 12, "text": "Child 1.2"},
                    ],
                },
                {
                    "id": 2,
                    "text": "Parent 2",
                    "expanded": True,
                    "children": [{"id": 21, "text": "Child 2.1"}],
                },
                {
                    "id": 3,
                    "text": "Parent 3",
                    "expanded": True,
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

    selection_model = tree_view.selectionModel()
    parent1 = model.item(0)
    child12 = parent1.child(1)
    child12_index = model.indexFromItem(child12)
    selection_model.select(
        child12_index,
        QItemSelectionModel.SelectionFlag.Select
        | QItemSelectionModel.SelectionFlag.Rows,
    )

    qtbot.waitUntil(lambda: selection_model.isSelected(child12_index), timeout=500)

    state["items"] = [state["items"][2], state["items"][0], state["items"][1]]

    qtbot.wait(200)

    def check_after_reorder():
        assert model.item(0).text() == "Parent 3"
        assert model.item(1).text() == "Parent 1"
        assert model.item(2).text() == "Parent 2"

        parent1_item = model.item(1)
        selected_child = parent1_item.child(1)
        selected_child_index = model.indexFromItem(selected_child)
        assert selected_child.text() == "Child 1.2"
        assert selection_model.isSelected(selected_child_index) is True
        assert len(selection_model.selectedRows()) == 1

    qtbot.waitUntil(check_after_reorder, timeout=1000)
