from functools import lru_cache


def camel_case(event, split, upper=False):
    prefix, *parts = event.split(split)
    return "".join(
        [prefix.capitalize() if upper else prefix]
        + [part.capitalize() for part in parts]
    )


@lru_cache(maxsize=None)
def attr_name_to_method_name(name, setter=False):
    sep = "-"
    if "_" in name:
        sep = "_"

    prefix = f"set{sep}" if setter else ""
    return camel_case(f"{prefix}{name}", sep)


def call_method(method, args):
    """Method that allows for calling setters/methods with multiple arguments
    such as: `setColumnStretch` of `PySide6.QtWidgets.QGridLayout` which takes a
    column and stretch argument.
    """
    if isinstance(args, tuple):
        method(*args)
    else:
        method(args)
