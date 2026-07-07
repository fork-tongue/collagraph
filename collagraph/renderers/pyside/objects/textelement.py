"""
Support for text elements as children of widgets that display text,
such as QLabel and QPushButton.

Text element proxies are kept in an ordered list on the parent widget
and the joined content of all of them is displayed by the parent
through its `setText` method.
Register insert and remove functions for more widget types (that have
a `setText` method) to support text elements as children.
"""

from PySide6.QtWidgets import QAbstractButton, QLabel

from ...pyside_renderer import PySideRenderer, TextElementProxy
from .widget import insert as widget_insert
from .widget import remove as widget_remove


@PySideRenderer.register_insert(QLabel, QAbstractButton)
def insert(self, el, anchor=None):
    if not isinstance(el, TextElementProxy):
        widget_insert(self, el, anchor=anchor)
        return

    if not hasattr(self, "_cg_text_proxies"):
        self._cg_text_proxies = []
    proxies = self._cg_text_proxies
    if anchor is not None and anchor in proxies:
        proxies.insert(proxies.index(anchor), el)
    else:
        proxies.append(el)
    el.set_parent(self)
    el.sync()


@PySideRenderer.register_remove(QLabel, QAbstractButton)
def remove(self, el):
    if not isinstance(el, TextElementProxy):
        widget_remove(self, el)
        return

    self._cg_text_proxies.remove(el)
    el.sync()
    el.set_parent(None)
