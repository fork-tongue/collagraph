"""
Example of how to render to PySide6 UI.
"""
from observ import reactive
from PySide6 import QtWidgets

from collagraph import Collagraph, create_element as h, EventLoopType
from collagraph.components import Component
from collagraph.renderers import PySideRenderer


def TodoList(props):
    # props.setdefault("layout_direction", "QBoxLayout.Direction.TopToBottom")
    return h(
        "Widget",
        {"layout_direction": "QBoxLayout.Direction.TopToBottom"},
        *[
            h(
                "Widget",
                {},
                h(
                    "Button",
                    {
                        "text": "✔️",
                        "checked": False,
                        "maximum-size": (40, 40),
                        "on_clicked": (lambda a: lambda: props["clicked"](a))(item),
                    },
                ),
                h("Label", {"text": item}),
            )
            for item in props["items"]
        ],
    )


class TodoApp(Component):
    def __init__(self, props):
        super().__init__(props)
        self.state = reactive(
            {
                "items": [
                    "Groceries",
                    "Laundry",
                ],
                "text": "",
            }
        )

    def handle_change(self, event):
        self.state["text"] = event

    def handle_submit(self, event):
        if todo := self.state["text"]:
            if todo in self.state["items"]:
                return
            self.state["items"].append(todo)
            self.state["text"] = ""

    def handle_complete(self, event):
        self.state["items"].remove(event)

    def render(self):
        return h(
            "Window",
            {"title": "My First TODO app"},
            h(
                "Widget",
                {
                    "name": "main-content",
                    "layout_direction": "QBoxLayout.Direction.TopToBottom",
                },
                h("Label", {"text": "What needs to be done?"}),
                h(
                    "LineEdit",
                    {
                        "text": self.state["text"],
                        "on_text_edited": lambda ev: self.handle_change(ev),
                    },
                ),
                h(
                    "Button",
                    {
                        "text": "Add",
                        "on_clicked": lambda ev: self.handle_submit(ev),
                    },
                ),
                h("Label", {"text": "TO DO:"}),
                h(
                    TodoList,
                    {
                        "items": self.state["items"],
                        "on_clicked": lambda ev: self.handle_complete(ev),
                        "clicked": lambda ev: self.handle_complete(ev),
                    },
                ),
            ),
        )


if __name__ == "__main__":
    app = QtWidgets.QApplication()

    gui = Collagraph(renderer=PySideRenderer(), event_loop_type=EventLoopType.QT)

    # Define Qt structure and map state to the structure
    element = h(TodoApp, {})

    # Pass in the app as a container. Can actually be any truthy object
    gui.render(element, app)
    app.exec()
