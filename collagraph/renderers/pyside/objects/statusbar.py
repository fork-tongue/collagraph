from . import widget


def insert(self, el, anchor=None):
    # TODO: support for anchor
    # if anchor:
    # action = self.insertWidget(anchor, el)
    # else:
    if getattr(el, "permanent", False):
        self.addPermanentWidget(el)
    else:
        self.addWidget(el)
    el.setParent(self)


def remove(self, el):
    el.setParent(None)


def set_attribute(self, attr, value):
    if attr == "text":
        # TODO: support for timeout arg?
        if isinstance(value, tuple):
            self.showMessage(*value)
        else:
            self.showMessage(value)
    else:
        widget.set_attribute(self, attr, value)
