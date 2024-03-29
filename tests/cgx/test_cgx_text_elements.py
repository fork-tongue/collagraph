from observ import reactive


def test_text_elements():
    from tests.data.text_elements import Example

    state = reactive({"content": "foo", "more": "bar"})

    component = Example(state)
    result = component.render()

    result.type == "div"

    static_p, dynamic_p, multiple_p, split_p = result.children

    assert static_p.type == "p"
    assert dynamic_p.type == "p"
    assert multiple_p.type == "p"
    assert split_p.type == "p"

    assert (
        len(static_p.children)
        == len(dynamic_p.children)
        == len(multiple_p.children)
        == 1
    )

    static, dynamic, multiple = (
        static_p.children[0],
        dynamic_p.children[0],
        multiple_p.children[0],
    )
    assert static.type == "TEXT_ELEMENT"
    assert dynamic.type == "TEXT_ELEMENT"
    assert multiple.type == "TEXT_ELEMENT"
    assert static.props["content"] == "Static content"
    assert dynamic.props["content"] == "Dynamic foo"
    assert multiple.props["content"] == r"Even bar dyna{}mic\{} foo"

    assert len(split_p.children) == 4
    assert split_p.children[0].type == "TEXT_ELEMENT"
    assert split_p.children[1].type == "TEXT_ELEMENT"
    assert split_p.children[2].type == "span"
    assert split_p.children[3].type == "TEXT_ELEMENT"
    assert split_p.children[0].props["content"] == "Split"
    assert split_p.children[1].props["content"] == " and split by "
    assert split_p.children[3].props["content"] == " element"
