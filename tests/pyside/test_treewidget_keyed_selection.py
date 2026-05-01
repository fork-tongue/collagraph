import pytest

pytest.importorskip("PySide6")

from observ import reactive
from PySide6 import QtWidgets

import collagraph as cg


def test_treewidget_keyed_vfor_with_selection(qtbot, parse_source):
    """
    Test that tree widget items with keyed v-for maintain correct selection
    when list changes.
    """
    element, _ = parse_source(
        """
        <treewidget>
          <treewidgetitem
            v-for="item in items"
            :key="item['id']"
            :selected="item['selected']"
            :content="{0: item['name']}"
          >
          </treewidgetitem>
        </treewidget>

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

    tree_widget = None
    items = []

    def find_tree_and_items():
        nonlocal tree_widget, items
        tree_widget = container.findChild(QtWidgets.QTreeWidget)
        assert tree_widget is not None
        assert tree_widget.topLevelItemCount() == 3
        items = [tree_widget.topLevelItem(i) for i in range(3)]
        assert all(item is not None for item in items)

    qtbot.waitUntil(find_tree_and_items, timeout=500)

    # Verify initial state
    def check_initial():
        assert items[0].text(0) == "Item A"
        assert items[0].isSelected() is True
        assert items[1].text(0) == "Item B"
        assert items[1].isSelected() is False
        assert items[2].text(0) == "Item C"
        assert items[2].isSelected() is False

    qtbot.waitUntil(check_initial, timeout=500)

    # Reorder the list - move Item A to the end
    state["items"] = [
        state["items"][1],  # B
        state["items"][2],  # C
        state["items"][0],  # A
    ]

    # Wait for reconciliation to complete
    qtbot.wait(200)

    def find_items_after_reorder():
        nonlocal items
        items = [tree_widget.topLevelItem(i) for i in range(3)]
        assert all(item is not None for item in items)

    qtbot.waitUntil(find_items_after_reorder, timeout=500)

    # After reordering, Item A should still be selected (it's now at index 2)
    def check_after_reorder():
        assert items[0].text(0) == "Item B"
        assert items[0].isSelected() is False, "Item B should not be selected"
        assert items[1].text(0) == "Item C"
        assert items[1].isSelected() is False, "Item C should not be selected"
        assert items[2].text(0) == "Item A"
        assert items[2].isSelected() is True, (
            "Item A should still be selected after reorder"
        )

    qtbot.waitUntil(check_after_reorder, timeout=500)


def test_treewidget_keyed_vfor_toggle_selection(qtbot, parse_source):
    """Test toggling selection state with keyed v-for."""
    element, _ = parse_source(
        """
        <treewidget>
          <treewidgetitem
            v-for="item in items"
            :key="item['id']"
            :selected="item['selected']"
            :content="{0: item['name']}"
          >
          </treewidgetitem>
        </treewidget>

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
                {"id": "a", "name": "Item A", "selected": False},
                {"id": "b", "name": "Item B", "selected": True},
                {"id": "c", "name": "Item C", "selected": False},
            ]
        }
    )

    container = renderer.create_element("widget")
    gui.render(element, container, state=state)

    tree_widget = None
    items = []

    def find_tree_and_items():
        nonlocal tree_widget, items
        tree_widget = container.findChild(QtWidgets.QTreeWidget)
        assert tree_widget is not None
        assert tree_widget.topLevelItemCount() == 3
        items = [tree_widget.topLevelItem(i) for i in range(3)]
        assert all(item is not None for item in items)

    qtbot.waitUntil(find_tree_and_items, timeout=500)

    # Verify initial state - B is selected
    def check_initial():
        assert items[1].isSelected() is True

    qtbot.waitUntil(check_initial, timeout=500)

    # Toggle selection: deselect B, select A and C
    state["items"][0]["selected"] = True
    state["items"][1]["selected"] = False
    state["items"][2]["selected"] = True

    # Verify selection changed
    def check_toggled():
        assert items[0].isSelected() is True, "Item A should be selected"
        assert items[1].isSelected() is False, "Item B should not be selected"
        assert items[2].isSelected() is True, "Item C should be selected"

    qtbot.waitUntil(check_toggled, timeout=500)


def test_treewidget_keyed_vfor_remove_selected_item(qtbot, parse_source):
    """Test removing a selected item from a keyed v-for list."""
    element, _ = parse_source(
        """
        <treewidget>
          <treewidgetitem
            v-for="item in items"
            :key="item['id']"
            :selected="item['selected']"
            :content="{0: item['name']}"
          >
          </treewidgetitem>
        </treewidget>

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
                {"id": "a", "name": "Item A", "selected": False},
                {"id": "b", "name": "Item B", "selected": True},
                {"id": "c", "name": "Item C", "selected": False},
            ]
        }
    )

    container = renderer.create_element("widget")
    gui.render(element, container, state=state)

    tree_widget = None
    items = []

    def find_tree_and_items():
        nonlocal tree_widget, items
        tree_widget = container.findChild(QtWidgets.QTreeWidget)
        assert tree_widget is not None
        assert tree_widget.topLevelItemCount() == 3
        items = [tree_widget.topLevelItem(i) for i in range(3)]
        assert all(item is not None for item in items)

    qtbot.waitUntil(find_tree_and_items, timeout=500)

    # Remove the selected item (Item B)
    state["items"].pop(1)

    def check_after_removal():
        assert tree_widget.topLevelItemCount() == 2
        item0 = tree_widget.topLevelItem(0)
        item1 = tree_widget.topLevelItem(1)
        assert item0.text(0) == "Item A"
        assert item0.isSelected() is False
        assert item1.text(0) == "Item C"
        assert item1.isSelected() is False

    qtbot.waitUntil(check_after_removal, timeout=500)


def test_treewidget_keyed_vfor_add_selected_item(qtbot, parse_source):
    """Test adding a selected item to a keyed v-for list."""
    element, _ = parse_source(
        """
        <treewidget>
          <treewidgetitem
            v-for="item in items"
            :key="item['id']"
            :selected="item['selected']"
            :content="{0: item['name']}"
          >
          </treewidgetitem>
        </treewidget>

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
                {"id": "a", "name": "Item A", "selected": False},
                {"id": "b", "name": "Item B", "selected": True},
            ]
        }
    )

    container = renderer.create_element("widget")
    gui.render(element, container, state=state)

    tree_widget = None

    def find_tree():
        nonlocal tree_widget
        tree_widget = container.findChild(QtWidgets.QTreeWidget)
        assert tree_widget is not None
        assert tree_widget.topLevelItemCount() == 2

    qtbot.waitUntil(find_tree, timeout=500)

    # Add a new selected item in the middle
    state["items"].insert(1, {"id": "c", "name": "Item C", "selected": True})

    def check_after_addition():
        assert tree_widget.topLevelItemCount() == 3
        item0 = tree_widget.topLevelItem(0)
        item1 = tree_widget.topLevelItem(1)
        item2 = tree_widget.topLevelItem(2)

        assert item0.text(0) == "Item A"
        assert item0.isSelected() is False
        assert item1.text(0) == "Item C"
        assert item1.isSelected() is True, "Newly added Item C should be selected"
        assert item2.text(0) == "Item B"
        assert item2.isSelected() is True, "Item B should still be selected"

    qtbot.waitUntil(check_after_addition, timeout=500)


def test_treewidget_keyed_vfor_with_expanded(qtbot, parse_source):
    """Test that expanded state works correctly with keyed v-for and reordering."""
    element, _ = parse_source(
        """
        <treewidget>
          <treewidgetitem
            v-for="item in items"
            :key="item['id']"
            :selected="item['selected']"
            :expanded="item['expanded']"
            :content="{0: item['name']}"
          >
            <treewidgetitem :content="{0: 'Child of ' + item['name']}">
            </treewidgetitem>
          </treewidgetitem>
        </treewidget>

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

    tree_widget = None
    items = []

    def find_tree_and_items():
        nonlocal tree_widget, items
        tree_widget = container.findChild(QtWidgets.QTreeWidget)
        assert tree_widget is not None
        assert tree_widget.topLevelItemCount() == 3
        items = [tree_widget.topLevelItem(i) for i in range(3)]
        assert all(item is not None for item in items)

    qtbot.waitUntil(find_tree_and_items, timeout=500)

    # Verify initial state
    def check_initial():
        assert items[0].text(0) == "Item A"
        assert items[0].isSelected() is True
        assert items[0].isExpanded() is True
        assert items[1].text(0) == "Item B"
        assert items[1].isSelected() is False
        assert items[1].isExpanded() is False
        assert items[2].text(0) == "Item C"
        assert items[2].isSelected() is False
        assert items[2].isExpanded() is True

    qtbot.waitUntil(check_initial, timeout=500)

    # Reverse the order
    state["items"].reverse()

    # Wait for reconciliation to complete
    qtbot.wait(200)

    def find_items_after_reverse():
        nonlocal items
        items = [tree_widget.topLevelItem(i) for i in range(3)]
        assert all(item is not None for item in items)

    qtbot.waitUntil(find_items_after_reverse, timeout=500)

    # After reversing, each item should maintain its selection and expanded state
    def check_after_reverse():
        assert items[0].text(0) == "Item C"
        assert items[0].isSelected() is False, "Item C should not be selected"
        assert items[0].isExpanded() is True, "Item C should be expanded"

        assert items[1].text(0) == "Item B"
        assert items[1].isSelected() is False, "Item B should not be selected"
        assert items[1].isExpanded() is False, "Item B should not be expanded"

        assert items[2].text(0) == "Item A"
        assert items[2].isSelected() is True, "Item A should still be selected"
        assert items[2].isExpanded() is True, "Item A should still be expanded"

    qtbot.waitUntil(check_after_reverse, timeout=500)
