from PySide6 import QtWidgets

import collagraph as cg

from examples.cgx_component_example import Example  # noqa: I100


if __name__ == "__main__":
    app = QtWidgets.QApplication()
    gui = cg.Collagraph(
        renderer=cg.PySideRenderer(),
        event_loop_type=cg.EventLoopType.QT,
    )
    gui.render(cg.h(Example, {"title": "SFC example"}), app)
    app.exec()
