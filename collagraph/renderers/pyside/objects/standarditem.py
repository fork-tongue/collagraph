from .qobject import set_attribute as qobject_set_attribute


def insert(self, el, anchor=None):
    if index := getattr(el, "model_index", None):
        self.setChild(*index, el)
        return

    if anchor is not None:
        index = None
        for row in range(self.rowCount()):
            if anchor == self.child(row):
                index = row
                break
        if index is None:
            return
        self.insertRow(index, el)
    else:
        self.appendRow(el)


def remove(self, el):
    if index := getattr(el, "model_index", None):
        # Only support removal of rows for now
        if model := el.model():
            index = model.indexFromItem(el)
            self.takeRow(index.row())
        return

    self.takeRow(el.row())


def set_attribute(self, attr, value):
    if attr == "model_index":
        if model := self.model():
            index = model.indexFromItem(self)
            if index.row() != value[0] or index.column() != value[1]:
                if parent := self.parent():
                    it = parent.takeChild(index.row(), index.column())
                    assert it == self
                    parent.setChild(*value, self)
                else:
                    it = model.takeItem(index.row(), index.column())
                    assert it == self
                    model.setItem(*value, it)

    qobject_set_attribute(self, attr, value)
