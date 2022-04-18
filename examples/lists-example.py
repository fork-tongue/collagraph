"""
Example of how to render to PySide6 UI.
"""
from observ import reactive
from PySide6 import QtWidgets

from collagraph import Collagraph, create_element as h, EventLoopType
from collagraph.renderers import PySideRenderer


def Example(props):
    def bump():
        props["items"].append(["NEW", "NEW"])

    def decr():
        if len(props["items"]):
            props["items"].pop()

    def item_changed(item):
        props["items"][item.row()][item.column()] = item.text()

    item_model = h(
        "QStandardItemModel",
        {
            "on_item_changed": item_changed,
            "column_count": len(props["items"][0]),
        },
        *[
            h("QStandardItem", {"text": item[0], "model_index": (i, 0)})
            for i, item in enumerate(props["items"])
        ],
        *[
            h("QStandardItem", {"text": item[1], "model_index": (i, 1)})
            for i, item in enumerate(props["items"])
        ]
    )

    return h(
        "Window",
        props,
        h(
            "Widget",
            {},
            h(
                "QSplitter",
                {},
                h(
                    "QListView",
                    {},
                    item_model,
                ),
                h(
                    "QTableView",
                    {},
                    item_model,
                ),
                h(
                    "QTreeView",
                    {},
                    item_model,
                ),
            ),
            h(
                "Widget",
                {"layout": {"type": "Box", "direction": "LeftToRight"}},
                h("Button", {"text": "Add", "on_clicked": bump}),
                h("Button", {"text": "Remove", "on_clicked": decr}),
            ),
        ),
    )


if __name__ == "__main__":
    app = QtWidgets.QApplication()

    gui = Collagraph(renderer=PySideRenderer(), event_loop_type=EventLoopType.QT)

    state = reactive(
        {
            "items": [
                ["Item", "Value"],
                ["Foo", "Bar"],
            ]
        }
    )

    # Define Qt structure and map state to the structure
    element = h(Example, state)

    # Pass in the app as a container. Can actually be any truthy object
    gui.render(element, app)
    app.exec()
