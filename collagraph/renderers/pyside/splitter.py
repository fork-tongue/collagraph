def insert(self, el, anchor=None):
    if anchor:
        index = self.indexOf(anchor)
        self.insertWidget(index, el)
    else:
        self.addWidget(el)
