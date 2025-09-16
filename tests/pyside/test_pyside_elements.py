import textwrap
from functools import partial

import pytest
from observ import reactive

PySide6 = pytest.importorskip("PySide6")

from PySide6 import QtCore, QtGui, QtWidgets

from collagraph import Collagraph
from collagraph import create_element as h
from collagraph.renderers import PySideRenderer
from collagraph.sfc import load_from_string


def get_current_window(app):
    """Returns the first instance of a window within the topLevelWidgets."""
    windows = []
    for widget in app.topLevelWidgets():
        if isinstance(widget, QtWidgets.QMainWindow):
            windows.append(widget)

    assert len(windows) <= 1
    return windows[0] if windows else None


def test_simple_structure(qtbot):
    renderer = PySideRenderer(autoshow=False)
    gui = Collagraph(renderer=renderer)

    container = renderer.create_element("Window")

    def Simple(props):
        return h("Widget", {"object_name": "simple"})

    gui.render(h(Simple, {}), container)

    def check_simple_is_child():
        simple = container.findChild(QtWidgets.QWidget, name="simple")
        assert simple
        assert simple.parent() is container

    qtbot.waitUntil(check_simple_is_child, timeout=500)


def test_layouts(qapp, qtbot):
    renderer = PySideRenderer(autoshow=False)
    gui = Collagraph(renderer=renderer)

    def LayoutExample(props):
        # Data to fill the box layout
        box = []
        for i in range(1, 5):
            box.append(("Button", {"text": f"Button {i}"}))

        # Data to fill the grid layout
        grid = []
        for i in range(1, 5):
            grid.append(("Label", {"text": f"Line {i}", "grid_index": (i, 0)}))
            grid.append(("LineEdit", {"grid_index": (i, 1)}))
        grid.append(
            (
                "TextEdit",
                {
                    "text": "This widget takes up about two thirds of the grid layout",
                    "grid_index": (1, 2, 4, 1),
                },
            )
        )

        # Data to fill the form layout
        form = []
        for i, widget in enumerate(["LineEdit", "ComboBox", "SpinBox"]):
            text = f"Line {i + 1}:"
            if i == 1:
                text = "Line 2, long text:"
            form.append((widget, {"form_label": text, "form_index": i}))

        return h(
            "Window",
            {},
            h(
                "Widget",
                {},
                h(
                    "GroupBox",
                    {
                        "title": "Horizontal layout",
                        "object_name": "box",
                        "layout": {
                            "type": "Box",
                            "direction": "LeftToRight",
                        },
                    },
                    *[h(item[0], item[1]) for item in box],
                ),
                h(
                    "GroupBox",
                    {
                        "title": "Grid layout",
                        "object_name": "grid",
                        "layout": {"type": "Grid"},
                    },
                    *[h(item[0], item[1]) for item in grid],
                ),
                h(
                    "GroupBox",
                    {
                        "title": "Form layout",
                        "object_name": "form",
                        "layout": {"type": "Form"},
                    },
                    *[h(item[0], item[1]) for item in form],
                ),
                h(
                    "TextEdit",
                    {
                        "text": "This widget takes up all the remaining "
                        "space in the top-level layout."
                    },
                ),
                h(
                    "DialogButtonBox",
                    {"buttons": ("Ok", "Cancel")},
                    h("Button", {"text": "Custom", "role": "ActionRole"}),
                ),
            ),
        )

    element = h(LayoutExample, {})
    gui.render(element, qapp)

    window = None

    def get_window():
        nonlocal window
        result = get_current_window(qapp)
        assert result
        window = result

    qtbot.waitUntil(get_window, timeout=500)

    def check_label():
        box = window.findChild(QtWidgets.QGroupBox, name="box")
        assert box
        assert isinstance(box.layout(), QtWidgets.QBoxLayout)
        grid = window.findChild(QtWidgets.QGroupBox, name="grid")
        assert grid
        assert isinstance(grid.layout(), QtWidgets.QGridLayout)
        form = window.findChild(QtWidgets.QGroupBox, name="form")
        assert form
        assert isinstance(form.layout(), QtWidgets.QFormLayout)

    qtbot.waitUntil(check_label, timeout=500)


def test_lists(qapp, qtbot, qtmodeltester):
    def ListsExample(props):
        def add_item():
            props["items"].append([["NEW", "ITEM"], False])

        def remove_item():
            if len(props["items"]):
                props["items"].pop(0)

        children = []
        for row, (item, _) in enumerate(props["items"]):
            for column, text in enumerate(item):
                children.append(
                    h("QStandardItem", {"text": text, "model_index": (row, column)})
                )

        item_model = h("QStandardItemModel", {"column_count": 2}, *children)

        return h(
            "Window",
            {},
            h(
                "Widget",
                {},
                h(
                    "QSplitter",
                    {},
                    h("QListView", {}, item_model),
                    h("QTableView", {}, item_model),
                    h("QTreeView", {}, item_model),
                ),
                h(
                    "Widget",
                    {
                        "layout": {
                            "type": "Box",
                            "direction": "LeftToRight",
                        },
                        "maximum-height": 50,
                    },
                    h(
                        "Button",
                        {"text": "Add", "on_clicked": add_item, "object_name": "add"},
                    ),
                    h(
                        "Button",
                        {
                            "text": "Remove",
                            "on_clicked": remove_item,
                            "object_name": "remove",
                        },
                    ),
                ),
            ),
        )

    renderer = PySideRenderer(autoshow=False)
    gui = Collagraph(renderer=renderer)

    state = reactive(
        {
            "items": [
                [["Foo", "Bar"], False],
            ],
        }
    )

    assert len(qapp.topLevelWidgets()) == 0

    element = h(ListsExample, state)
    gui.render(element, qapp)

    window = None
    model = None

    # Check that Foo in in the model
    def check_model_contains_foo():
        nonlocal window
        nonlocal model

        window = get_current_window(qapp)
        assert window

        list_view = window.findChild(QtWidgets.QListView)
        model = list_view.model()

        assert model.findItems("Foo")
        assert model.findItems("Bar", column=1)
        qtmodeltester.check(model)

    qtbot.waitUntil(check_model_contains_foo, timeout=500)

    add_button = None
    remove_button = None

    def find_buttons():
        nonlocal add_button
        nonlocal remove_button

        add_button = window.findChild(QtWidgets.QPushButton, name="add")
        assert add_button
        remove_button = window.findChild(QtWidgets.QPushButton, name="remove")
        assert remove_button

    qtbot.waitUntil(find_buttons, timeout=500)
    qtbot.mouseClick(add_button, QtCore.Qt.LeftButton)

    # Check that NEW is added to the model
    def check_model_contains_new():
        assert model.findItems("Foo")
        assert model.findItems("Bar", column=1)
        assert model.findItems("NEW")
        assert model.findItems("ITEM", column=1)
        qtmodeltester.check(model)

    qtbot.waitUntil(check_model_contains_new, timeout=500)
    qtbot.mouseClick(remove_button, QtCore.Qt.LeftButton)

    # Check that Foo is removed from the model
    def check_model_does_not_contain_foo():
        assert not model.findItems("Foo")
        assert not model.findItems("Bar", column=1)
        assert model.findItems("NEW")
        assert model.findItems("ITEM", column=1)
        qtmodeltester.check(model)

    qtbot.waitUntil(check_model_does_not_contain_foo, timeout=500)


def test_menu(qapp, qtbot):
    def MenuExample(props):
        return h(
            "Window",
            {},
            h(
                "QMenuBar",
                {},
                h(
                    "QMenu",
                    {"title": "File"},
                    h(
                        "QAction",
                        {"text": "Open"},
                    ),
                ),
            ),
            h(
                "Widget",
                {},
            ),
        )

    renderer = PySideRenderer(autoshow=False)
    gui = Collagraph(renderer=renderer)
    gui.render(h(MenuExample, {}), qapp)

    def check_file_menu():
        windows = [
            widget
            for widget in qapp.topLevelWidgets()
            if isinstance(widget, QtWidgets.QMainWindow)
        ]
        assert len(windows) == 1
        actions = windows[0].findChildren(QtGui.QAction)
        assert any([action.text() == "Open" for action in actions])

    qtbot.waitUntil(check_file_menu, timeout=500)


def test_menu_extensively(qapp, qtbot):
    from tests.data.menubar import MenuBarTest

    state = reactive(
        {
            "show_menubar": True,
            "show_menu": True,
            "show_item": True,
            "show_submenu": True,
            "show_subitem": True,
        }
    )
    renderer = PySideRenderer(autoshow=False)
    gui = Collagraph(renderer=renderer)
    gui.render(h(MenuBarTest, state), qapp)

    def check(menubar, menu, item, submenu, subitem):
        windows = [
            widget
            for widget in qapp.topLevelWidgets()
            if isinstance(widget, QtWidgets.QMainWindow)
        ]
        assert len(windows) == 1
        assert menubar is bool(windows[0].findChild(QtWidgets.QMenuBar, "menubar"))
        assert item is bool(windows[0].findChild(QtGui.QAction, "action"))
        assert subitem is bool(windows[0].findChild(QtGui.QAction, "subaction"))

    check_items = partial(check, True, True, True, True, True)
    qtbot.waitUntil(check_items, timeout=500)

    state["show_subitem"] = False

    check_items = partial(check, True, True, True, True, False)
    qtbot.waitUntil(check_items, timeout=500)

    state["show_submenu"] = False
    state["show_subitem"] = True

    check_items = partial(check, True, True, True, False, False)
    qtbot.waitUntil(check_items, timeout=500)

    state["show_menu"] = False

    check_items = partial(check, True, False, False, False, False)
    qtbot.waitUntil(check_items, timeout=500)

    state["show_menu"] = True
    state["show_menubar"] = False

    check_items = partial(check, False, False, False, False, False)
    qtbot.waitUntil(check_items, timeout=500)


def test_app(qapp, qtbot):
    from tests.data.app import Window

    renderer = PySideRenderer(autoshow=False)
    gui = Collagraph(renderer=renderer)
    gui.render(h(Window), qapp)

    window = None

    def check():
        nonlocal window
        windows = [
            widget
            for widget in qapp.topLevelWidgets()
            if isinstance(widget, QtWidgets.QMainWindow)
        ]
        assert len(windows) == 1
        window = windows[0]

    qtbot.waitUntil(check, timeout=500)

    def check_name(type, name, show):
        obj = window.findChild(type, name)
        assert show == bool(obj)

    qtbot.waitUntil(
        partial(check_name, type=QtWidgets.QWidget, name="dock_title", show=True),
        timeout=500,
    )
    dock = window.findChild(QtGui.QAction, "toggle_dock_title")
    dock.triggered.emit()

    qtbot.waitUntil(
        partial(check_name, type=QtWidgets.QWidget, name="dock_title", show=False),
        timeout=500,
    )

    qtbot.waitUntil(
        partial(check_name, type=QtWidgets.QStatusBar, name="statusbar", show=True),
        timeout=500,
    )

    statusbar = window.findChild(QtGui.QAction, "toggle_statusbar")
    statusbar.triggered.emit()

    qtbot.waitUntil(
        partial(check_name, type=QtWidgets.QStatusBar, name="statusbar", show=False),
        timeout=500,
    )

    qtbot.waitUntil(
        partial(check_name, type=QtGui.QAction, name="action", show=True),
        timeout=500,
    )

    action = window.findChild(QtGui.QAction, "toggle_action")
    action.triggered.emit()

    qtbot.waitUntil(
        partial(check_name, type=QtGui.QAction, name="action", show=False),
        timeout=500,
    )

    qtbot.waitUntil(
        partial(check_name, type=QtWidgets.QToolBar, name="toolbar", show=True),
        timeout=500,
    )

    toolbar = window.findChild(QtGui.QAction, "toggle_toolbar")
    toolbar.triggered.emit()

    qtbot.waitUntil(
        partial(check_name, type=QtWidgets.QToolBar, name="toolbar", show=False),
        timeout=500,
    )

    qtbot.waitUntil(
        partial(check_name, type=QtWidgets.QWidget, name="dock_content", show=True),
        timeout=500,
    )
    dock = window.findChild(QtGui.QAction, "toggle_dock_content")
    dock.triggered.emit()

    qtbot.waitUntil(
        partial(check_name, type=QtWidgets.QWidget, name="dock_content", show=False),
        timeout=500,
    )

    qtbot.waitUntil(
        partial(check_name, type=QtWidgets.QDockWidget, name="dock", show=True),
        timeout=500,
    )

    dock = window.findChild(QtGui.QAction, "toggle_dock")
    dock.triggered.emit()

    qtbot.waitUntil(
        partial(check_name, type=QtWidgets.QDockWidget, name="dock", show=False),
        timeout=500,
    )


def test_scroll_area(qapp, qtbot):
    App, _ = load_from_string(
        textwrap.dedent(
            """
            <template>
              <scrollarea>
                <label
                  v-if="label"
                />
                <textedit
                  v-else-if="edit"
                />
              </scrollarea>
            </template>

            <script>
            import collagraph as cg

            class App(cg.Component):
                pass
            </script>
            """
        )
    )

    state = reactive({"label": True, "edit": True})

    renderer = PySideRenderer(autoshow=False)
    gui = Collagraph(renderer=renderer)
    gui.render(h(App, state), qapp)

    scroll_area = None

    def check():
        nonlocal scroll_area
        windows = [
            widget
            for widget in qapp.topLevelWidgets()
            if isinstance(widget, QtWidgets.QScrollArea)
        ]
        assert len(windows) == 1, windows
        scroll_area = windows[0]

    qtbot.waitUntil(check, timeout=500)

    qtbot.waitUntil(
        lambda: isinstance(scroll_area.widget(), QtWidgets.QLabel),
        timeout=500,
    )

    state["label"] = False

    qtbot.waitUntil(
        lambda: isinstance(scroll_area.widget(), QtWidgets.QTextEdit),
        timeout=500,
    )

    state["edit"] = False

    qtbot.waitUntil(
        lambda: scroll_area.widget() is None,
        timeout=500,
    )
