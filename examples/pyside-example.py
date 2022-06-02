"""
Example of how to render to PySide6 UI.
"""
from observ import reactive
from PySide6 import QtCore, QtWidgets

import collagraph as cg
from collagraph import h


app = QtWidgets.QApplication()


def PushButton(props):
    text = props.get("text", "Push me")
    on_clicked = props.get("on_clicked")
    enabled = on_clicked is not None

    return h(
        "Button",
        {"text": text, "on_clicked": on_clicked, "enabled": enabled},
    )


if __name__ == "__main__":
    renderer = cg.PySideRenderer()
    gui = cg.Collagraph(renderer=renderer, event_loop_type=cg.EventLoopType.QT)

    # Define top-level actions
    def improve_content(checked):
        if "world" in state["title"]["text"]:
            state["title"]["text"] = "Hello handsome!"
        elif "there" in state["title"]["text"]:
            state["title"]["text"] = "Hello there!"

        if "PySide6" in state["content"]["text"]:
            state["content"]["text"] = state["content"]["text"].replace(
                "a PySide6", "an awesome"
            )
        elif " is " in state["content"]["text"]:
            state["content"]["text"] = state["content"]["text"].replace(" is ", " was ")
            state["button"]["on_clicked"] = None

    # Define some state
    state = reactive(
        {
            "title": {
                "text": "Hello world!",
            },
            "content": {
                # Each attribute will be split by '-', resulting parts capitalized,
                # and then prefixed with 'set' to construct the 'setter' method that
                # gets called to set the value. So, for instance, 'text' will become:
                # 'setText' and 'text-interaction-flags' will become
                # 'setTextInteractionFlags'.
                "text": "This is a PySide6 example",
                "text-interaction-flags": QtCore.Qt.TextSelectableByMouse,
                # TODO: The selection does not seem to work completely yet :/
                "selection": (10, 7),
            },
            # Use prefix 'on' with the signal name to attach a callback / slot
            # to the signal of the created PySide element
            "button": {"on_clicked": improve_content},
        }
    )

    # Define Qt structure and map state to the structure
    element = h(
        "Window",
        {},
        h(
            "Widget",
            {},
            h("Label", state["title"]),
            h("Label", state["content"]),
            h(PushButton, state["button"]),
        ),
    )

    # Pass in the app as a container. Can actually be any truthy object
    gui.render(element, app)
    app.exec()
