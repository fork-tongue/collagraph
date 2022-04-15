def insert(self, el, anchor=None):
    index = -1
    label = ""
    if hasattr(el, "tab_index"):
        index = el.tab_index
    if hasattr(el, "tab_label"):
        label = el.tab_label

    if index >= 0:
        self.insertTab(index, el, label)
    else:
        self.addTab(el, label)


def remove(self, el):
    index = self.indexOf(el)
    if index >= 0:
        self.removeTab(index)
