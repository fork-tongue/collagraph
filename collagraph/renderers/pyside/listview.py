from PySide6.QtGui import QStandardItemModel


def insert(self, el, anchor=None):
    model = self.model()
    if not model:
        model = QStandardItemModel(self)
        self.setModel(model)

        # TODO: This should probably be part of pyside_renderer's
        # 'add_event_listener' or maybe that function needs
        # to be mapped as well, such as the 'insert', 'remove'
        # and 'set_attribute' methods...

        # Make sure to try to connect event listeners from the
        # list view to signals from the item model, such as
        # 'itemChanged'.
        if slots := getattr(self, "slots", None):
            for event_type in slots:
                if signal := getattr(model, event_type, None):
                    for slot in slots[event_type]:
                        signal.connect(slot)

    # TODO: list with multiple columns?
    if anchor:
        index = model.indexFromItem(anchor)
        model.insertRow(index.row(), el)
    else:
        model.appendRow(el)


def remove(self, el):
    index = self.model().indexFromItem(el)
    self.model().takeRow(index.row())
