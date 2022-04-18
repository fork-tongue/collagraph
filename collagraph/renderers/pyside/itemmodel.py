from PySide6.QtGui import QStandardItem, QStandardItemModel


def insert(self, el, anchor=None):
    assert isinstance(el, QStandardItem)

    # TODO: This should probably be part of pyside_renderer's
    # 'add_event_listener' or maybe that function needs
    # to be mapped as well, such as the 'insert', 'remove'
    # and 'set_attribute' methods...

    # Make sure to try to connect event listeners from the
    # list view to signals from the item model, such as
    # 'itemChanged'.
    # if slots := getattr(self, "slots", None):
    #     for event_type in slots:
    #         if signal := getattr(model, event_type, None):
    #             for slot in slots[event_type]:
    #                 signal.connect(slot)

    # TODO: list with multiple columns?
    if isinstance(self, QStandardItemModel):
        if index := getattr(el, "model_index", None):
            self.setItem(*index, el)
            return

        if anchor:
            index = self.indexFromItem(anchor)
            self.insertRow(index.row(), el)
        else:
            self.appendRow(el)
    else:
        raise NotImplementedError(type(self).__name__)


def remove(self, el):
    index = self.indexFromItem(el)
    self.takeRow(index.row())
