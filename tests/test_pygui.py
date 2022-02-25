import pygui


def test_basic_dict_renderer():
    renderer = pygui.renderers.DictRenderer()
    gui = pygui.PyGui(renderer=renderer, sync=True)

    element = pygui.create_element("app")

    container = {"type": "root"}

    gui.render(element, container)

    assert container["children"][0] == {"type": "app"}
