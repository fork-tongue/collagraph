def insert(self, el, anchor=None):
    # TODO: support separators
    if anchor:
        self.insertMenu(anchor, el)
    else:
        self.addMenu(el)
