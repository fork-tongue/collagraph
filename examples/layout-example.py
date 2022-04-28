"""
Example of how to render to PySide6 UI and utilize
the layout of widgets.
"""
from PySide6 import QtWidgets

import collagraph as cg
from collagraph import h


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
        text = f"Line {i+1}:"
        if i == 1:
            text = "Line 2, long text:"
        form.append((widget, {"form_label": text, "form_index": i}))

    return h(
        "Window",
        {},
        h(
            "MenuBar",
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
            h(
                "GroupBox",
                {
                    "title": "Horizontal layout",
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
                    "layout": {
                        "type": "Grid",
                        # Other possible props:
                        # - row_stretch
                        # - column_minimum_width
                        # - row_minimum_height
                        # - vertical_spacing
                        # - horizontal_spacing
                        "column_stretch": [(1, 10), (2, 20)],
                    },
                },
                *[h(item[0], item[1]) for item in grid],
            ),
            h(
                "GroupBox",
                {
                    "title": "Form layout",
                    "layout": {
                        "type": "Form",
                    },
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
                {},
                h("Button", {"flag": "Ok"}),
                h("Button", {"flag": "Cancel"}),
            ),
        ),
    )


if __name__ == "__main__":
    app = QtWidgets.QApplication()

    gui = cg.Collagraph(
        renderer=cg.PySideRenderer(), event_loop_type=cg.EventLoopType.QT
    )

    # Define Qt structure and map state to the structure
    element = h(LayoutExample, {})

    # Pass in the app as a container. Can actually be any truthy object
    gui.render(element, app)
    app.exec()
