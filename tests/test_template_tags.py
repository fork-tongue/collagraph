from observ import reactive

import collagraph as cg


def test_component_template_tag():
    from tests.data.template import Template

    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"more": False})
    element = cg.h(Template, state)

    gui.render(element, container)

    content = container["children"][0]
    assert content["type"] == "content"

    assert len(content["children"]) == 2
    for child, name in zip(content["children"], ["a", "b"]):
        assert child["type"] == "child"
        assert child["attrs"]["name"] == name

    state["more"] = True

    assert len(content["children"]) == 4
    for child, name in zip(content["children"], ["a", "b", "c", "d"]):
        assert child["type"] == "child"
        assert child["attrs"]["name"] == name
