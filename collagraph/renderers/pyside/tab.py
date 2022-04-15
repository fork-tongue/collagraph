def insert(self, el, anchor=None):
    index = getattr(el, "tab_index", -1)
    label = getattr(el, "tab_label", "")

    if index >= 0:
        self.insertTab(index, el, label)
    else:
        self.addTab(el, label)


def remove(self, el):
    index = self.indexOf(el)
    if index >= 0:
        self.removeTab(index)
