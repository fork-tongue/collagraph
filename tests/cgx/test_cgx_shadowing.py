import importlib
from types import ModuleType
import warnings

from observ import reactive
import pytest

from collagraph.cgx import cgx


def test_warn_on_shadow_import():
    cgx.CGX_RUNTIME_WARNINGS = True

    import tests.data.shadow_imports

    # The module might have already been imported, so
    # in order to make sure that the generated code has
    # no runtime warnings in it, it needs to be reloaded
    importlib.reload(tests.data.shadow_imports)

    state = reactive({"tests": "baz"})

    example = tests.data.shadow_imports.Example(state)
    with pytest.warns(UserWarning) as records:
        result = example.render()

    assert len(records) == 3

    assert result.type == "widget"
    assert result.props["data"] != "foo"
    assert result.props["data"] != "bar"
    assert result.props["data"] != "baz"
    assert isinstance(result.props["data"], ModuleType)


def test_disable_warnings():
    cgx.CGX_RUNTIME_WARNINGS = False

    import tests.data.shadow_imports

    # The module might have already been imported, so
    # in order to make sure that the generated code has
    # no runtime warnings in it, it needs to be reloaded
    importlib.reload(tests.data.shadow_imports)

    state = reactive({"tests": "bar"})

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        example = tests.data.shadow_imports.Example(state)
        example.render()
