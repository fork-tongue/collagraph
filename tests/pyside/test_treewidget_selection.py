import pytest

pytest.importorskip("PySide6")

from observ import reactive
from PySide6 import QtWidgets

import collagraph as cg


def test_treewidget_selection_state(qtbot, parse_source):
    """
    Test that tree widget item selection state can be changed through reactive state.
    """
    element, _ = parse_source(
        """
        <treewidget>
          <treewidgetitem :selected="item1_selected" :content="{0: 'Item 1'}">
          </treewidgetitem>
          <treewidgetitem :selected="item2_selected" :content="{0: 'Item 2'}">
          </treewidgetitem>
          <treewidgetitem :selected="item3_selected" :content="{0: 'Item 3'}">
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
            "item1_selected": True,
            "item2_selected": False,
            "item3_selected": True,
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

    # Verify initial selection state
    def check_initial_selection():
        assert items[0].isSelected() is True
        assert items[1].isSelected() is False
        assert items[2].isSelected() is True

    qtbot.waitUntil(check_initial_selection, timeout=500)

    # Change selection state through reactive state
    state["item1_selected"] = False
    state["item2_selected"] = True
    state["item3_selected"] = False

    # Verify selection state changed
    def check_updated_selection():
        assert items[0].isSelected() is False
        assert items[1].isSelected() is True
        assert items[2].isSelected() is False

    qtbot.waitUntil(check_updated_selection, timeout=500)

    # Toggle again to make sure it works both ways
    state["item1_selected"] = True
    state["item2_selected"] = False

    def check_final_selection():
        assert items[0].isSelected() is True
        assert items[1].isSelected() is False

    qtbot.waitUntil(check_final_selection, timeout=500)


def test_treewidget_expanded_state(qtbot, parse_source):
    """
    Test that tree widget item expanded state can be changed through reactive state.
    """
    element, _ = parse_source(
        """
        <treewidget>
          <treewidgetitem :expanded="item1_expanded" :content="{0: 'Parent 1'}">
            <treewidgetitem :content="{0: 'Child 1'}">
            </treewidgetitem>
          </treewidgetitem>
          <treewidgetitem :expanded="item2_expanded" :content="{0: 'Parent 2'}">
            <treewidgetitem :content="{0: 'Child 2'}">
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
            "item1_expanded": True,
            "item2_expanded": False,
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
        assert tree_widget.topLevelItemCount() == 2
        items = [tree_widget.topLevelItem(i) for i in range(2)]
        assert all(item is not None for item in items)

    qtbot.waitUntil(find_tree_and_items, timeout=500)

    # Verify initial expanded state
    def check_initial_expanded():
        assert items[0].isExpanded() is True
        assert items[1].isExpanded() is False

    qtbot.waitUntil(check_initial_expanded, timeout=500)

    # Change expanded state through reactive state
    state["item1_expanded"] = False
    state["item2_expanded"] = True

    # Verify expanded state changed
    def check_updated_expanded():
        assert items[0].isExpanded() is False
        assert items[1].isExpanded() is True

    qtbot.waitUntil(check_updated_expanded, timeout=500)


def test_treewidget_selection_and_expanded_combined(qtbot, parse_source):
    """Test that both selection and expanded states work together correctly."""
    element, _ = parse_source(
        """
        <treewidget>
          <treewidgetitem
            :selected="selected"
            :expanded="expanded"
            :content="{0: 'Parent Item'}"
          >
            <treewidgetitem :content="{0: 'Child Item'}">
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
            "selected": True,
            "expanded": True,
        }
    )

    container = renderer.create_element("widget")
    gui.render(element, container, state=state)

    tree_widget = None
    item = None

    def find_tree_and_item():
        nonlocal tree_widget, item
        tree_widget = container.findChild(QtWidgets.QTreeWidget)
        assert tree_widget is not None
        assert tree_widget.topLevelItemCount() == 1
        item = tree_widget.topLevelItem(0)
        assert item is not None

    qtbot.waitUntil(find_tree_and_item, timeout=500)

    # Verify initial state
    def check_initial_state():
        assert item.isSelected() is True
        assert item.isExpanded() is True

    qtbot.waitUntil(check_initial_state, timeout=500)

    # Change both states
    state["selected"] = False
    state["expanded"] = False

    # Verify both states changed
    def check_updated_state():
        assert item.isSelected() is False
        assert item.isExpanded() is False

    qtbot.waitUntil(check_updated_state, timeout=500)

    # Toggle back
    state["selected"] = True
    state["expanded"] = True

    def check_final_state():
        assert item.isSelected() is True
        assert item.isExpanded() is True

    qtbot.waitUntil(check_final_state, timeout=500)
