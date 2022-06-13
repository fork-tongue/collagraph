from types import ModuleType

from observ import reactive
import pytest


def test_warn_on_shadow_import():
    from tests.data.shadow_imports import Example

    state = reactive({"tests": "bar"})

    example = Example(state)
    with pytest.warns(UserWarning) as records:
        result = example.render()

    assert len(records) == 2

    assert result.type == "widget"
    assert result.props["data"] != "foo"
    assert result.props["data"] != "bar"
    assert isinstance(result.props["data"], ModuleType)
