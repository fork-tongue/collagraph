from . import attr_name_to_method_name, call_method


def set_attribute(self, attr, value):
    method_name = attr_name_to_method_name(attr, setter=True)
    method = getattr(self, method_name, None)
    if not method:
        setattr(self, attr, value)
        return

    call_method(method, value)
