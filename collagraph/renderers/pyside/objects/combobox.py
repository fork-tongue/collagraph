from . import widget


def set_attribute(self, attr, value):
    if attr == "items":
        self.addItems(value)
    else:
        widget.set_attribute(self, attr, value)
