"""
Counter example written with the pure-Python view API
(the equivalent of counter.cgx, without a template).

Run this example as follows:
uv run python examples/pyside/counter_view.py
"""

from PySide6 import QtWidgets

import collagraph as cg
from collagraph import h


class Counter(cg.Component):
    def init(self):
        self.state["count"] = 0

    def bump(self):
        self.state["count"] += 1

    def view(self):
        with h.widget():
            h.label(lambda: f"Count: {self.state['count']}")
            h.button("bump", on_clicked=self.bump)


if __name__ == "__main__":
    app = QtWidgets.QApplication()
    gui = cg.Collagraph(renderer=cg.PySideRenderer())
    gui.render(Counter, app)
    app.exec()
