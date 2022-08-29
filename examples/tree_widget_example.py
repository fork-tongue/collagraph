from PySide6 import QtWidgets

import collagraph as cg

from examples.tree_widget import TreeWidget  # noqa: I100


if __name__ == "__main__":
    app = QtWidgets.QApplication()
    gui = cg.Collagraph(renderer=cg.PySideRenderer())
    gui.render(cg.h(TreeWidget, {}), app)
    app.exec()
