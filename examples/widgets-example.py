"""
Example of how to render to PySide6 UI.
"""
from observ import reactive
from PySide6 import QtWidgets

from collagraph import Collagraph, create_element as h, EventLoopType
from collagraph.renderers import PySideRenderer


def Example(props):
    def bump():
        props["tab_count"] += 1

    def decr():
        props["tab_count"] = max(props["tab_count"] - 1, 0)

    return h(
        "Window",
        props,
        h(
            "Widget",
            {},
            h(
                "QTabWidget",
                {},
                *[
                    h(
                        "Widget",
                        {
                            "tab_label": f"Tab {i+1}",
                            "tab_index": i,
                        },
                        h("Label", {"text": f"Content of tab {i+1}"}),
                    )
                    for i in range(props["tab_count"])
                ],
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

    state = reactive({"tab_count": 2})

    # Define Qt structure and map state to the structure
    element = h(Example, state)

    # Pass in the app as a container. Can actually be any truthy object
    gui.render(element, app)
    app.exec()
