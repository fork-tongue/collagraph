"""
TODO app written with the pure-Python view API (the equivalent of
todo_example.cgx and todo_list.cgx, without templates).

Run this example as follows:
uv run python examples/pyside/todo_view.py
"""

from PySide6 import QtWidgets

import collagraph as cg
from collagraph import h


class TodoList(cg.Component):
    def complete(self, item):
        self.emit("clicked", item)

    def view(self):
        with h.widget():

            @cg.each(lambda: self.props["items"], key=lambda item: item)
            def _(item):
                with h.widget(layout={"type": "Box", "direction": "LeftToRight"}):
                    h.button(
                        text="✔️",
                        checked=False,
                        maximum_size=(40, 40),
                        on_clicked=lambda: self.complete(item()),
                    )
                    h.label(text=item)


class TodoApp(cg.Component):
    def init(self):
        self.state["items"] = [
            "Groceries",
            "Laundry",
        ]
        self.state["text"] = ""

    def handle_change(self, text):
        self.state["text"] = text

    def handle_submit(self):
        if todo := self.state["text"]:
            if todo in self.state["items"]:
                return
            self.state["items"].append(todo)
            self.state["text"] = ""

    def handle_complete(self, item):
        self.state["items"].remove(item)

    def view(self):
        with h.window(window_title="My first TODO app"):
            with h.widget(name="main-content"):
                h.label(text="What do you want to do?")
                h.lineedit(
                    text=lambda: self.state["text"],
                    on_text_edited=self.handle_change,
                )
                h.button(text="Add", on_clicked=self.handle_submit)
                with cg.when(lambda: len(self.state["items"]) > 0):
                    h.label(text="To do:")
                    h(
                        TodoList,
                        items=lambda: self.state["items"],
                        on_clicked=self.handle_complete,
                    )
                with cg.otherwise():
                    h.label(text="All done! 🎉")


if __name__ == "__main__":
    app = QtWidgets.QApplication()
    gui = cg.Collagraph(renderer=cg.PySideRenderer())
    gui.render(TodoApp, app)
    app.exec()
