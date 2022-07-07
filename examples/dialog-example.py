import collagraph as cg
from PySide6 import QtWidgets  # noqa: I100, I201

from examples.dialog_example_window import Window  # noqa: I100, I202


app = QtWidgets.QApplication()

state = {
    "items": ["A", "B", "C"],
    "file": None,
}
gui = cg.Collagraph(renderer=cg.PySideRenderer())
gui.render(cg.h(Window, {"items": state["items"]}), app)

app.exec()
