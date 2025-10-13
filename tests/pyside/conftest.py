import warnings

import pytest


@pytest.fixture(scope="function", autouse=True)
def qapp(qapp_args, qapp_cls, pytestconfig, qtbot):
    # workaround for https://bugreports.qt.io/browse/PYSIDE-2575
    import asyncio

    from PySide6 import QtCore
    from PySide6.QtAsyncio import QAsyncioEventLoopPolicy
    from PySide6.QtWidgets import QMainWindow
    from pytestqt.qt_compat import qt_api

    app = qt_api.QtWidgets.QApplication.instance()
    assert app is not None
    # Check that there are not left-over widgets from other tests
    assert len(app.topLevelWidgets()) == 0

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        policy = asyncio.get_event_loop_policy()
        if not isinstance(policy, QAsyncioEventLoopPolicy):
            asyncio.set_event_loop_policy(QAsyncioEventLoopPolicy())

    yield app

    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            widget.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        widget.close()
        widget.deleteLater()

    # Process events to make sure that widgets will be cleaned up
    app.processEvents()

    qtbot.waitUntil(lambda: len(app.topLevelWidgets()) == 0, timeout=500)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        asyncio.set_event_loop_policy(None)
