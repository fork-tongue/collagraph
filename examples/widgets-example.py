"""
Example of how to render to PySide6 UI.
"""
from PySide6 import QtWidgets

from collagraph import Collagraph, create_element as h, EventLoopType
from collagraph.renderers import PySideRenderer


def Example(props):
    return h(
        "Window",
        {},
        h(
            "Widget",
            {},
            h(
                "QTabWidget",
                {},
                h(
                    "Widget",
                    {
                        "tab_label": "Tab 2",
                        "tab_index": 1,
                    },
                    h("Label", {"text": "Content of tab 1"}),
                ),
                h(
                    "Widget",
                    {
                        "tab_label": "Tab 1",
                        "tab_index": 0,
                    },
                    h("Label", {"text": "Content of tab 2"}),
                ),
            ),
        ),
    )


if __name__ == "__main__":
    app = QtWidgets.QApplication()

    gui = Collagraph(renderer=PySideRenderer(), event_loop_type=EventLoopType.QT)

    # Define Qt structure and map state to the structure
    element = h(Example, {})

    # Pass in the app as a container. Can actually be any truthy object
    gui.render(element, app)
    app.exec()
