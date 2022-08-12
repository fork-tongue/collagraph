def insert(self, el, anchor=None):
    if index := getattr(el, "model_index", None):
        self.setRowCount(max(self.rowCount(), index[0]))
        self.setColumnCount(max(self.columnCount(), index[1]))
        self.setChild(*index, el)
        return

    if anchor:
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
        self.takeChild(*index)
        return

    self.takeRow(el.row())
