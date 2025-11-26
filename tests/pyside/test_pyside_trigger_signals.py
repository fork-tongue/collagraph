from functools import partial

import pytest
from observ import reactive

pytest.importorskip("PySide6")

from PySide6 import QtWidgets

import collagraph as cg

TREE_WIDGET = """
<treewidget @item-changed="item_changed">
  <treewidgetitem
    v-for="item in items"
    :content="{0: item}"
  />
</treewidget>

<script>
import collagraph as cg

class Tree(cg.Component):
    changed = 0

    def init(self):
        pass

    def item_changed(self, item, column):
        Tree.changed += 1
</script>
"""

TREE_VIEW = """
<treeview>
  <itemmodel @item_changed="item_changed">
    <standarditem
      v-for="item in items"
      :text="item"
    />
  </itemmodel>
</treewidget>

<script>
import collagraph as cg

class Tree(cg.Component):
    changed = 0

    def init(self):
        pass

    def item_changed(self, item):
        Tree.changed += 1
</script>
"""


def tree_widget_nr_items_found(container, count):
    tree_widget = container.findChild(QtWidgets.QTreeWidget)
    assert tree_widget
    root_item = tree_widget.invisibleRootItem()
    assert root_item.childCount() == count


def tree_view_nr_items_found(container, count):
    tree_widget = container.findChild(QtWidgets.QTreeView)
    assert tree_widget
    model = tree_widget.model()
    assert model.rowCount() == count


def test_qtreewidgetitem_change_list_no_trigger(qtbot, parse_source):
    """
    When a qstandarditem is adjusted by the renderer, it should not trigger any signals.
    """
    Tree, _ = parse_source(TREE_WIDGET)
    state = reactive({"items": ["a", "b", "c", "d"]})

    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)
    container = renderer.create_element("widget")
    gui.render(Tree, container, state=state)
    assert Tree.changed == 0

    qtbot.waitUntil(partial(tree_widget_nr_items_found, container, 4), timeout=500)
    assert Tree.changed == 0

    state["items"].pop(2)
    assert Tree.changed == 0

    qtbot.waitUntil(partial(tree_widget_nr_items_found, container, 3), timeout=500)
    assert Tree.changed == 0

    # Edit the text of the first item, which should trigger the itemChanged signal
    tree_widget = container.findChild(QtWidgets.QTreeWidget)
    root_item = tree_widget.invisibleRootItem()
    first_item = root_item.child(0)
    first_item.setText(0, "e")
    assert Tree.changed == 1


def test_qtreewidgetitem_change_item_no_trigger(qtbot, parse_source):
    """
    When a qstandarditem is adjusted by the renderer, it should not trigger any signals.
    """
    Tree, _ = parse_source(TREE_WIDGET)
    state = reactive({"items": ["a", "b", "c", "d"]})

    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)
    container = renderer.create_element("widget")
    gui.render(Tree, container, state=state)
    assert Tree.changed == 0

    qtbot.waitUntil(partial(tree_widget_nr_items_found, container, 4), timeout=500)
    assert Tree.changed == 0

    def item_in_list(index: int, value: str):
        tree_widget = container.findChild(QtWidgets.QTreeView)
        assert tree_widget
        root_item = tree_widget.invisibleRootItem()
        item = root_item.child(index)
        assert item.text(0) == value, item.text(0)

    state["items"][2] = "e"
    assert Tree.changed == 0

    qtbot.waitUntil(partial(item_in_list, 2, "e"), timeout=500)
    assert Tree.changed == 0

    # Edit the text of the first item, which should trigger the itemChanged signal
    tree_widget = container.findChild(QtWidgets.QTreeWidget)
    root_item = tree_widget.invisibleRootItem()
    first_item = root_item.child(0)
    first_item.setText(0, "e")
    assert Tree.changed == 1


def test_qstandarditem_change_list_no_trigger(qtbot, parse_source):
    """
    When a qstandarditem is adjusted by the renderer, it should not trigger any signals.
    """
    Tree, _ = parse_source(TREE_VIEW)
    state = reactive({"items": ["a", "b", "c", "d"]})

    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)
    container = renderer.create_element("widget")
    gui.render(Tree, container, state=state)
    assert Tree.changed == 0

    qtbot.waitUntil(partial(tree_view_nr_items_found, container, 4), timeout=500)
    assert Tree.changed == 0

    state["items"].pop(2)
    assert Tree.changed == 0

    qtbot.waitUntil(partial(tree_view_nr_items_found, container, 3), timeout=500)
    assert Tree.changed == 0

    # Edit the text of the first item, which should trigger the itemChanged signal
    tree_view = container.findChild(QtWidgets.QTreeView)
    model = tree_view.model()
    item_index = model.index(0, 0)
    model.setItemData(item_index, {0: "e"})
    assert Tree.changed == 1


def test_qstandarditem_change_item_no_trigger(qtbot, parse_source):
    """
    When a qstandarditem is adjusted by the renderer, it should not trigger any signals.
    """
    Tree, _ = parse_source(TREE_VIEW)
    state = reactive({"items": ["a", "b", "c", "d"]})

    renderer = cg.PySideRenderer(autoshow=False)
    gui = cg.Collagraph(renderer=renderer)
    container = renderer.create_element("widget")
    gui.render(Tree, container, state=state)
    assert Tree.changed == 0

    qtbot.waitUntil(partial(tree_view_nr_items_found, container, 4), timeout=500)
    assert Tree.changed == 0

    def item_in_list(index: int, value: str):
        tree_widget = container.findChild(QtWidgets.QTreeView)
        assert tree_widget
        model = tree_widget.model()
        assert model.hasIndex(index, 0)
        item_index = model.index(index, 0)
        assert model.itemData(item_index)[0] == value, model.itemData(item_index)

    state["items"][2] = "e"
    assert Tree.changed == 0

    qtbot.waitUntil(partial(item_in_list, 2, "e"), timeout=500)
    assert Tree.changed == 0

    # Edit the text of the first item, which should trigger the itemChanged signal
    tree_view = container.findChild(QtWidgets.QTreeView)
    model = tree_view.model()
    item_index = model.index(0, 0)
    model.setItemData(item_index, {0: "e"})
    assert Tree.changed == 1
