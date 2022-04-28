"""
Example that shows slider, progress bar and spinbox that
are connected to the same value.
"""
from observ import reactive
from PySide6 import QtCore, QtWidgets

import collagraph as cg
from collagraph import h


def Example(props):
    def value_changed(value):
        props["value"] = value

    def tracking_changed(value):
        props["tracking"] = value

    return h(
        "Window",
        props,
        h(
            "Widget",
            {},
            h(
                "Slider",
                {
                    "orientation": QtCore.Qt.Orientation.Horizontal,
                    "minimum": 0,
                    "maximum": 100,
                    "value": props["value"],
                    "on_value_changed": value_changed,
                    "tracking": props["tracking"],
                },
            ),
            h(
                "CheckBox",
                {
                    "text": "slider tracking",
                    "checked": props["tracking"],
                    "on_state_changed": tracking_changed,
                },
            ),
            h(
                "SpinBox",
                {
                    "minimum": 0,
                    "maximum": 100,
                    "value": props["value"],
                    "on_value_changed": value_changed,
                },
            ),
            h(
                "ProgessBar",
                {
                    "minimum": 0,
                    "maximum": 100,
                    "value": props["value"],
                    "on_value_changed": value_changed,
                },
            ),
        ),
    )


if __name__ == "__main__":
    app = QtWidgets.QApplication()

    gui = cg.Collagraph(
        renderer=cg.PySideRenderer(), event_loop_type=cg.EventLoopType.QT
    )
    state = reactive({"value": 50, "tracking": True})
    element = h(Example, state)

    gui.render(element, app)
    app.exec()
