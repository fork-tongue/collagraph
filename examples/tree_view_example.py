from PySide6 import QtWidgets

import collagraph as cg

from examples.tree_view import TreeView  # noqa: I100


if __name__ == "__main__":
    app = QtWidgets.QApplication()
    gui = cg.Collagraph(
        renderer=cg.PySideRenderer(),
        event_loop_type=cg.EventLoopType.QT,
    )
    gui.render(cg.h(TreeView, {}), app)
    app.exec()
