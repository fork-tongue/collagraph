def test_cgx_callbacks():
    from tests.data.callbacks import Example

    example = Example({})
    output = example.render()

    button_one, button_two, button_three = output.children

    button_one.props["on_clicked"]()

    assert Example.callbacks[-1] == ("clicked", "one")

    button_two.props["on_clicked"]("clicked")

    assert Example.callbacks[-1] == ("clicked", "two")

    button_three.props["on_clicked"]("clicked")

    assert Example.callbacks[-1] == ("clicked", "three")
