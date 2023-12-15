from PySide6 import QtWidgets

import collagraph as cg


if __name__ == "__main__":
    from tests.data.app import Window

    app = QtWidgets.QApplication()
    gui = cg.Collagraph(
        renderer=cg.PySideRenderer(),
        event_loop_type=cg.EventLoopType.QT,
    )
    gui.render(cg.h(Window), app)
    app.exec()
