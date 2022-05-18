from PySide6 import QtWidgets

import collagraph as cg

from debug_example import DebugExample  # noqa: I100


if __name__ == "__main__":
    app = QtWidgets.QApplication()

    gui = cg.Collagraph(
        renderer=cg.PySideRenderer(),
        event_loop_type=cg.EventLoopType.QT,
    )
    gui.render(cg.h(DebugExample), app)

    app.exec()
