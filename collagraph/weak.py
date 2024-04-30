from functools import wraps
from inspect import signature
from weakref import ref


def weak(obj):
    """
    Prevent the strong capture of the given object
    by using a weakref.ref instead.
    This decorator assumes the first argument to the method
    to be argument for which a weak ref is made.

    The wrapper method will actually have it's first argument
    popped, with the assumption that it will coincide with the
    weak ref object.

    The wrapped method will then be called, only if the
    weak ref object is actually still alive.

    Example usage:

        @weak(self)
        def callback(self):
            print(self)

    This will ensure the callback function does not capture
    a strong reference to self.
    """
    weak_obj = ref(obj)

    def wrapper(method):
        sig = signature(method)
        non_default_parameters = [
            par for par in sig.parameters.values() if par.default is par.empty
        ]
        nr_arguments = len(non_default_parameters)

        if nr_arguments == 0:
            raise TypeError(
                "Make sure that wrapped method takes 'self' as first argument"
            )

        elif nr_arguments == 1:

            @wraps(method)
            def wrapped():
                if this := weak_obj():
                    return method(this)

            return wrapped
        elif nr_arguments == 2:

            @wraps(method)
            def wrapped(new):
                if this := weak_obj():
                    return method(this, new)

            return wrapped
        elif nr_arguments == 3:

            @wraps(method)
            def wrapped(new, old):
                if this := weak_obj():
                    return method(this, new, old)

            return wrapped
        else:
            raise NotImplementedError

    return wrapper
