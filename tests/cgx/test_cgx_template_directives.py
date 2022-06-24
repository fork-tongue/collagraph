from observ import reactive
import pytest


import collagraph as cg


def test_directive_bind():
    from tests.data.directive_bind import Labels

    component = Labels({"text": "Custom label"})
    node = component.render()

    assert node.type == "widget"

    first_label = node.children[0]
    second_label = node.children[1]

    assert first_label.props["text"] == "Custom label"
    assert second_label.props["text"] == "Custom label"


def test_directive_typo():
    # Would be most excellent if the typo could already
    # be detected at import, but that can only work if
    # the component can define all props and state...
    from tests.data.directive_typo import Label

    component = Label({})
    with pytest.raises(NameError):
        component.render()


def test_directive_bind_context():
    from tests.data.directive_bind_context import Labels

    component = Labels({})
    node = component.render()

    assert node.type == "widget"
    assert node.props["layout"]

    first_label = node.children[0]
    second_label = node.children[1]

    assert first_label.props["text"] == "Label"
    assert second_label.props["text"] == cg.__version__


def test_directive_bind_state_and_props():
    from tests.data.directive_bind_state_and_props import Labels

    component = Labels({"text": "Custom label"})
    node = component.render()

    assert node.type == "widget"

    first_label = node.children[0]
    second_label = node.children[1]

    assert first_label.props["text"] == "Custom label"
    assert second_label.props["text"] == "Custom label"


def test_directive_bind_full():
    from tests.data.directive_bind_multiple import Labels

    component = Labels({"text": "foo", "other": "bar"})
    node = component.render()

    assert node.type == "widget"

    first_label = node.children[0]
    second_label = node.children[1]
    third_label = node.children[2]

    assert first_label.props["text"] == "foo"
    assert second_label.props["text"] == "bar"
    assert third_label.props["text"] == "foo"


def test_directive_if():
    from tests.data.directive_if import Label

    state = reactive({"show": True})
    component = Label(state)
    node = component.render()

    assert node.type == "widget"

    assert len(node.children) == 1
    assert node.children[0].type == "label"
    assert node.children[0].props["text"] == "Foo"

    state["show"] = False
    node = component.render()

    assert len(node.children) == 0


def test_directive_if_elaborate():
    from tests.data.directive_if_elaborate import Label

    state = reactive({"show": True})
    component = Label(state)
    node = component.render()

    assert node.type == "widget"

    assert len(node.children) == 2
    assert node.children[0].type == "label"
    assert node.children[0].props["text"] == "Foo"
    assert node.children[1].props["text"] == "Bar"

    state["show"] = False
    node = component.render()

    assert len(node.children) == 1

    assert node.children[0].props["text"] == "Bar"


def test_directive_else():
    from tests.data.directive_else import Label

    state = reactive({"show": True})
    component = Label(state)
    node = component.render()

    assert node.type == "widget"

    assert len(node.children) == 1
    assert node.children[0].type == "label"
    assert node.children[0].props["text"] == "Foo"

    state["show"] = False
    node = component.render()

    assert len(node.children) == 1
    assert node.children[0].type == "label"
    assert node.children[0].props["text"] == "Bar"


def test_directive_else_if():
    from tests.data.directive_else_if import Label

    state = reactive({"foo": True, "bar": True, "baz": True})
    component = Label(state)
    node = component.render()

    assert node.type == "widget"

    assert len(node.children) == 1
    assert node.children[0].type == "label"
    assert node.children[0].props["text"] == "Foo"

    state["foo"] = False
    node = component.render()

    assert len(node.children) == 1
    assert node.children[0].type == "label"
    assert node.children[0].props["text"] == "Bar"

    state["bar"] = False
    node = component.render()

    assert len(node.children) == 1
    assert node.children[0].type == "label"
    assert node.children[0].props["text"] == "Baz"

    state["baz"] = False
    node = component.render()

    assert len(node.children) == 1
    assert node.children[0].type == "label"
    assert node.children[0].props["text"] == "Bas"


def test_directive_for():
    from tests.data.directive_for import Labels

    state = reactive({"labels": []})
    component = Labels(state)
    node = component.render()

    assert node.type == "widget"

    assert len(node.children) == 0

    for labels in (["Foo"], ["Foo", "Bar"], []):
        state["labels"] = labels
        node = component.render()

        assert len(node.children) == len(labels)
        for idx, label in enumerate(labels):
            assert node.children[idx].props["text"] == label


def test_directive_for_with_enumerate():
    from tests.data.directive_for_enumerate import Labels

    state = reactive({"labels": []})
    component = Labels(state)
    node = component.render()

    assert node.type == "widget"

    assert len(node.children) == 0

    for labels in (["Foo"], ["Foo", "Bar"], []):
        state["labels"] = labels
        node = component.render()

        assert len(node.children) == len(labels)
        for idx, label in enumerate(labels):
            assert node.children[idx].props["text"] == label


def test_directive_for_elaborate():
    from tests.data.directive_for_elaborate import Labels

    state = reactive({"labels": [], "suffixes": []})
    component = Labels(state)
    node = component.render()

    assert node.type == "widget"

    assert len(node.children) == 0

    for labels, suffixes in (
        (["Foo"], ["x"]),
        (["Foo", "Bar"], ["x", "y"]),
        ([], []),
        (["a", "b", "c", "d"], ["1", "2", "3", "4"]),
    ):
        state["labels"] = labels
        state["suffixes"] = suffixes
        node = component.render()

        assert len(node.children) == len(labels)
        for idx, (label, suffix) in enumerate(zip(labels, suffixes)):
            assert node.children[idx].props["text"] == label
            assert node.children[idx].props["suffix"] == suffix


def test_directive_for_nested():
    from tests.data.directive_for_nested import Labels

    state = reactive({"rows": [["a", "b", "c"], ["d", "e"]]})
    component = Labels(state)
    node = component.render()

    assert len(node.children) == 2
    assert len(node.children[0].children) == 3
    assert len(node.children[1].children) == 2

    assert node.children[0].children[0].children[0].props["text"] == "0,0: a"
    assert node.children[0].children[1].children[0].props["text"] == "1,0: b"
    assert node.children[0].children[2].children[0].props["text"] == "2,0: c"
    assert node.children[1].children[0].children[0].props["text"] == "0,1: d"
    assert node.children[1].children[1].children[0].props["text"] == "1,1: e"


def test_directive_on():
    from tests.data.directive_on import Buttons

    component = Buttons({})
    node = component.render()

    add_button = node.children[0]
    sub_button = node.children[1]

    assert component.state["count"] == 0
    assert add_button.props["text"] == "Add"
    assert sub_button.props["text"] == "Sub"

    assert add_button.props["on_clicked"]
    assert sub_button.props["on_clicked"]

    add_button.props["on_clicked"]()

    assert component.state["count"] == 1

    sub_button.props["on_clicked"]()

    assert component.state["count"] == 0


def test_directive_boolean_casting():
    from tests.data.directive_boolean_casting import Labels

    component = Labels({})
    node = component.render()

    assert node.type == "widget"
    assert len(node.children) == 1

    label = node.children[0]
    assert "disabled" in label.props
    assert label.props["disabled"] is True
