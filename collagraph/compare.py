from functools import partial
from typing import Callable


def equivalent_functions(a: Callable, b: Callable):
    """Returns whether function a is equivalent to function b.

    ``functools.partial`` functions are also supported (but only when both
    argument a and b are partial).
    """
    if not hasattr(a, "__code__") or not hasattr(b, "__code__"):
        if isinstance(a, partial) and isinstance(b, partial):
            return (
                a.args == b.args
                and a.keywords == b.keywords
                and equivalent_functions(a.func, b.func)
            )

        return a == b

    return equivalent_code(a.__code__, b.__code__) and equivalent_closure_values(a, b)


def equivalent_code(a, b):
    """Returns True if a and b are equivalent code.

    In order to determine this, a number of properties are compared that
    should be equal between similar functions.
    It checks all co_* props of __code__ (as seen in Python 3.9), except for:
      * co_firstlineno
      * co_lnotab
      * co_name
    because those vars can differ without having any impact on the equivalency
    of the functions themselves.
    """
    for attr in {
        "co_varnames",
        "co_argcount",
        "co_cellvars",
        "co_code",
        "co_consts",
        "co_filename",
        "co_flags",
        "co_freevars",
        "co_kwonlyargcount",
        "co_names",
        "co_nlocals",
        "co_posonlyargcount",
        "co_stacksize",
    }:
        attr_a = getattr(a, attr, None)
        attr_b = getattr(b, attr, None)
        if attr in {"co_freevars", "co_varnames"}:
            # co_varnames and co_freevars can contain names, which might
            # be different but should be similar at least in length
            if len(attr_a) != len(attr_b):
                return False
        elif attr_a != attr_b:
            return False

    return True


def equivalent_closure_values(a, b):
    """Compare the cell contents of the __closure__ attribute for the given
    functions. This method assumes that the code for a and be is already
    equivalent."""
    if (closure_a := getattr(a, "__closure__", None)) and (
        closure_b := getattr(b, "__closure__", None)
    ):
        values_a = [cell.cell_contents for cell in closure_a]
        values_b = [cell.cell_contents for cell in closure_b]
        if len(values_a) != len(values_b):
            return False

        for a, b in zip(values_a, values_b):
            if callable(a) and callable(b):
                if not equivalent_functions(a, b):
                    return False
            else:
                if a != b:
                    return False

    return True
