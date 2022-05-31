import pytest


@pytest.fixture(autouse=True)
def qt_app(qapp, qtbot):
    from PySide6.QtWidgets import QMainWindow
    from PySide6 import QtCore

    # Check that there are not left-over widgets from other tests
    assert len(qapp.topLevelWidgets()) == 0

    yield qapp

    # Make sure to clear / delete all widgets after each test
    for widget in qapp.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            widget.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        widget.close()
        widget.deleteLater()

    # Process events to make sure that widgets will be cleaned up
    qapp.processEvents()

    qtbot.waitUntil(lambda: len(qapp.topLevelWidgets()) == 0, timeout=500)
