from observ import reactive


def test_resolve_names():
    from tests.data.resolve_names import Example

    state = reactive({"prop_val": "prop_value"})

    example = Example(state)
    root = example.render()

    item = root.children[0]
    assert item.props["value"] == "prop_value", item
    item = root.children[1]
    assert item.props["value"] == "state_value", item
    item = root.children[2]
    assert item.props["value"] == "value", item

    item = root.children[3]
    assert item.props["value"] == "prop_value", item
    item = root.children[4]
    assert item.props["value"] == "state_value", item
    item = root.children[5]
    assert item.props["value"] == "value", item
