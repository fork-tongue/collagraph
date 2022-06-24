def insert(self, el, anchor=None):
    if getattr(el, "title", False):
        self.setTitleBarWidget(el)
    else:
        self.setWidget(el)
    el.setParent(self)


def remove(self, el):
    el.setParent(None)
