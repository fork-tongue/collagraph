from observ import reactive
import pytest


def test_directive_bind():
    from tests.data.directive_bind import Labels

    component = Labels({})
    node = component.render()

    assert node.type == "widget"

    first_label = node.children[0]
    second_label = node.children[1]

    assert first_label.props["text"] == "Label"
    assert second_label.props["text"] == "Label"


def test_directive_if():
    from tests.data.directive_if import Label

    state = reactive({"show": True})
    component = Label(state)
    node = component.render()

    assert node.type == "widget"

    assert len(node.children) == 1
    node.children[0].type == "label"
    node.children[0].props["text"] == "Foo"

    state["show"] = False
    node = component.render()

    assert len(node.children) == 0


@pytest.mark.xfail
def test_directive_else():
    from tests.data.directive_else import Label

    state = reactive({"show": True})
    component = Label(state)
    node = component.render()

    assert node.type == "widget"

    assert len(node.children) == 1
    node.children[0].type == "label"
    node.children[0].props["text"] == "Foo"

    state["show"] = False
    node = component.render()

    assert len(node.children) == 1
    node.children[0].type == "label"
    node.children[0].props["text"] == "Bar"


@pytest.mark.xfail
def test_directive_else_if():
    from tests.data.directive_else_if import Label

    state = reactive({"foo": True, "bar": True})
    component = Label(state)
    node = component.render()

    assert node.type == "widget"

    assert len(node.children) == 1
    node.children[0].type == "label"
    node.children[0].props["text"] == "Foo"

    state["foo"] = False
    node = component.render()

    assert len(node.children) == 1
    node.children[0].type == "label"
    node.children[0].props["text"] == "Bar"

    state["bar"] = False
    node = component.render()

    assert len(node.children) == 1
    node.children[0].type == "label"
    node.children[0].props["text"] == "Baz"


@pytest.mark.xfail
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


@pytest.mark.xfail
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
