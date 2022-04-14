from PySide6.QtWidgets import QDialogButtonBox


def insert(self, el, anchor=None):
    if hasattr(el, "flag"):
        self.addButton(getattr(QDialogButtonBox, el.flag))
        return
    elif hasattr(el, "role"):
        self.addButton(el, getattr(QDialogButtonBox, el.role))
        return
    raise NotImplementedError
