from functools import partial

from collagraph.compare import equivalent_functions


def test_compare_functions():
    def a():
        return 2

    def b():
        return 2

    c = lambda: 2  # noqa: E731

    assert equivalent_functions(a, b)
    assert equivalent_functions(a, c)
    assert equivalent_functions(b, c)

    val = 3

    def a():
        return val

    assert not equivalent_functions(a, b)

    def b():
        return val

    assert equivalent_functions(a, b)
    assert equivalent_functions(a, lambda: val)
    assert not equivalent_functions(a, lambda: val + 1)


def test_lambda_functions_with_closures():
    collection = {}

    def create(number):
        collection[number] = lambda: number * 2

    for x in range(2):
        create(x)

    assert collection[0]() != collection[1]()
    assert not equivalent_functions(collection[0], collection[1])


def test_partial_functions():
    callbacks = []

    def double(a):
        return a * 2

    for x in range(3):
        callbacks.append(partial(double, x))

    assert not equivalent_functions(callbacks[0], callbacks[1])

    other = partial(double, 2)
    assert equivalent_functions(other, callbacks[2])

    def another_double(b):
        return b * 2

    another = partial(another_double, 2)
    assert equivalent_functions(other, another)


def test_mix_partial_lambda():
    def a(x):
        return x * 2

    b = partial(a)

    assert not equivalent_functions(a, b)


def test_similar_lambda_functions():
    # Different multiplier
    a = lambda x: x * 2  # noqa: E731
    b = lambda x: x * 3  # noqa: E731

    assert not equivalent_functions(a, b)

    # Same multiplier but different var name
    # should still result in the same bytecode
    b = lambda y: y * 2  # noqa: E731
    assert equivalent_functions(a, b)

    # Switching the order around will produce
    # different bytecode, although the other
    b = lambda y: 2 * y  # noqa: E731
    assert not equivalent_functions(a, b)


def test_closures():
    def outer(value):
        val = value

        def inner():
            return val

        return inner

    a = outer("a")
    b = outer("b")

    assert a() == "a"
    assert b() == "b"

    assert not equivalent_functions(a, b)


def test_similar_lambda_function_which_captures_other_function():
    def double(a):
        return a * 2

    def other_double(b):
        return b * 2

    def add(c):
        return c + 2

    x = lambda a: double(a)  # noqa: E731
    y = lambda b: other_double(b)  # noqa: E731
    z = lambda c: add(c)  # noqa: E731

    assert equivalent_functions(x, y)
    assert not equivalent_functions(x, z)
    assert not equivalent_functions(y, z)
