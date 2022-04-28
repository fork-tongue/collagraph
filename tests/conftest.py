import asyncio

import pytest


async def miniloop():
    await asyncio.sleep(0)


@pytest.fixture
def process_events():
    loop = asyncio.get_event_loop_policy().get_event_loop()

    def run():
        loop.run_until_complete(miniloop())

    yield run


@pytest.fixture
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

    qtbot.waitUntil(lambda: len(qapp.topLevelWidgets()) == 0, timeout=500)
